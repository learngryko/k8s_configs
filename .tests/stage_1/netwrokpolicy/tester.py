import subprocess
import sys
import time
import concurrent.futures

NAMESPACES = ["dev", "prod", "monitoring"]
POD_IMAGE = "nicolaka/netshoot:latest"
TEST_DOMAIN = "google.com"
PODS_PER_NS = 2
DEBUG_LOG_FILE = "debug.log"

def short_name(ns, idx):
    return f"{ns}-{idx}"

def podname(ns, idx):
    return f"test-pod-{idx}-{ns}"

def run(cmd):
    try:
        out = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT, timeout=30)
        return out.decode()
    except subprocess.CalledProcessError as e:
        return e.output.decode()
    except Exception as ex:
        return str(ex)

def create_test_pod(namespace, podname):
    print(f"Creating test pod: {podname} in ns {namespace}")
    run(f"kubectl -n {namespace} delete pod {podname} --ignore-not-found")
    pod_yaml = f"""
apiVersion: v1
kind: Pod
metadata:
  name: {podname}
spec:
  containers:
    - name: test
      image: {POD_IMAGE}
      command: ["sleep", "3600"]
      securityContext:
        runAsUser: 1000
        runAsGroup: 3000
        allowPrivilegeEscalation: false
        capabilities:
          drop: ["ALL"]
        runAsNonRoot: true
        seccompProfile:
          type: RuntimeDefault
  securityContext:
    runAsNonRoot: true
    fsGroup: 2000
"""
    with open(f"/tmp/{podname}.yaml", "w") as f:
        f.write(pod_yaml)
    run(f"kubectl -n {namespace} apply -f /tmp/{podname}.yaml")
    for _ in range(30):
        pods = run(f"kubectl -n {namespace} get pods -o name")
        if f"pod/{podname}" not in pods:
            time.sleep(1)
            continue
        phase = run(f"kubectl -n {namespace} get pod {podname} -o jsonpath='{{.status.phase}}'")
        if "Running" in phase:
            return True
        time.sleep(1)
    logs = run(f"kubectl -n {namespace} describe pod {podname}")
    print(f"[ERROR] Pod {podname} did not start in ns {namespace}")
    print(logs)
    return False

def delete_test_pod(namespace, podname):
    run(f"kubectl -n {namespace} delete pod {podname} --ignore-not-found")

def get_pod_ip(namespace, podname):
    ip = run(f"kubectl -n {namespace} get pod {podname} -o=jsonpath='{{.status.podIP}}'")
    return ip.strip()

def exec_pod(namespace, podname, cmd):
    full_cmd = f"kubectl -n {namespace} exec {podname} -- {cmd}"
    result = run(full_cmd)
    with open(DEBUG_LOG_FILE, "a") as dbg:
        dbg.write(f"[DEBUG] exec {namespace}/{podname}: {cmd} => {repr(result)}\n")
    return result


def parse_ping_result(output):
    # Try to decide if ICMP worked based on typical ping output
    debug_reason = []
    # True if any of these say "packets received"
    if "0% packet loss" in output:
        debug_reason.append("Found '0% packet loss'")
        return True, debug_reason
    for x in ["1 received", "2 received", "3 received"]:
        if x in output:
            debug_reason.append(f"Found '{x}'")
            return True, debug_reason
    if "bytes from" in output:
        debug_reason.append("Found 'bytes from'")
        return True, debug_reason
    # Otherwise, looks blocked
    debug_reason.append("No valid ICMP response")
    return False, debug_reason

def test_ping(src_ns, src_idx, dst_ns, dst_idx, dst_ip):
    src_pod = podname(src_ns, src_idx)
    out = exec_pod(src_ns, src_pod, f"ping -c 3 -w 5 {dst_ip}")
    allowed, debug_reason = parse_ping_result(out)
    # Print out *everything* about this test
    print(f"Test: {src_pod} ({src_ns}) -> {dst_ip} (of {dst_ns}) | Allowed: {allowed} | Reason: {debug_reason}")
    print(f"Raw output:\n{out.strip()}\n---")
    # Also write to debug.log
    with open(DEBUG_LOG_FILE, "a") as dbg:
        dbg.write(f"[RESULT] {src_pod} -> {dst_ip} : ALLOWED={allowed}, reason={debug_reason}\n")
    return allowed

def print_matrix_and_summary(results, src_labels, dst_labels, allowed_set):
    cell_width = 13
    header = " " * (max(len(s) for s in src_labels) + 2)
    print("\n=== Network Policy Matrix (ping) ===")
    print(header, end="")
    for dst in dst_labels:
        print(dst.ljust(cell_width), end="")
    print()
    for i, src in enumerate(src_labels):
        print(src.ljust(max(len(s) for s in src_labels) + 2), end="")
        for j, dst in enumerate(dst_labels):
            cell = "ALLOWED" if results[i][j] else "BLOCKED"
            print(cell.ljust(cell_width), end="")
        print()
    total = len(src_labels) * len(dst_labels)
    allowed = sum(sum(row) for row in results)
    blocked = total - allowed
    print("\n=== Network Policy Test Summary ===")
    print(f"Total connections tested: {total}")
    print(f"BLOCKED: {blocked}")
    print(f"ALLOWED: {allowed}")
    if allowed_set:
        print("Unexpectedly ALLOWED connections:")
        for src, dst in allowed_set:
            print(f" - {src} -> {dst}")
    else:
        print("No unexpected ALLOWED connections.\n")

def main():
    open(DEBUG_LOG_FILE, "w").close()  # Clean log

    pod_ips = {}  # (ns, idx) -> ip
    src_labels = []
    dst_labels = []

    print("=== Creating test pods ===")
    for ns in NAMESPACES:
        for idx in range(1, PODS_PER_NS + 1):
            p_name = podname(ns, idx)
            ok = create_test_pod(ns, p_name)
            print(f"Pod creation {p_name} result: {ok}")
            if not ok:
                print(f"[FATAL] Cannot create pod {p_name}. Aborting.")
                sys.exit(1)

    print("Waiting 5 seconds for network and DNS stabilization...")
    time.sleep(5)

    print("\n=== DNS Tests ===")
    for ns in NAMESPACES:
        for idx in range(1, PODS_PER_NS + 1):
            p_name = podname(ns, idx)
            print(f"DNS test for {p_name} in {ns}: ", end="")
            test_dns(ns, p_name)
            pod_ip = get_pod_ip(ns, p_name)
            pod_ips[(ns, idx)] = pod_ip
            print(f"Pod IP for {p_name}: {pod_ip}")
            lbl = short_name(ns, idx)
            if lbl not in src_labels:
                src_labels.append(lbl)
            if lbl not in dst_labels:
                dst_labels.append(lbl)

    results_matrix = [[False for _ in dst_labels] for _ in src_labels]
    allowed_set = set()
    print("\n=== Connectivity matrix (ping, parallel) ===")

    def test_dns(namespace, podname):
        print(f"Testing DNS in {namespace} ({podname}) ... ", end="")
        res = exec_pod(namespace, podname, f"nslookup {TEST_DOMAIN}")
        if "Name:" in res or "name =" in res:
            print("✅ DNS OK")
            return True
        else:
            print("❌ DNS BLOCKED")
            return False

    def test_ping(src_ns, src_idx, dst_ns, dst_idx, dst_ip):
        src_pod = podname(src_ns, src_idx)
        res = exec_pod(src_ns, src_pod, f"ping -c 3 -w 5 {dst_ip}")
        allowed = "0% packet loss" in res or "1 received" in res or "2 received" in res or "3 received" in res
        return allowed

    test_cases = []
    for src_ns in NAMESPACES:
        for src_idx in range(1, PODS_PER_NS + 1):
            src_lbl = short_name(src_ns, src_idx)
            for dst_ns in NAMESPACES:
                for dst_idx in range(1, PODS_PER_NS + 1):
                    dst_lbl = short_name(dst_ns, dst_idx)
                    dst_ip = pod_ips[(dst_ns, dst_idx)]
                    test_cases.append((src_ns, src_idx, dst_ns, dst_idx, dst_ip, src_lbl, dst_lbl))

    with concurrent.futures.ThreadPoolExecutor(max_workers=16) as executor:
        future_to_case = {
            executor.submit(test_ping, *args[:5]): args for args in test_cases
        }
        for future in concurrent.futures.as_completed(future_to_case):
            args = future_to_case[future]
            src_lbl = args[5]
            dst_lbl = args[6]
            i = src_labels.index(src_lbl)
            j = dst_labels.index(dst_lbl)
            allowed = future.result()
            # Debug print for matrix writing:
            print(f"Matrix update: {src_lbl}({i}) -> {dst_lbl}({j}) = {allowed}")
            results_matrix[i][j] = allowed
            if allowed and not (src_lbl == dst_lbl):
                allowed_set.add((src_lbl, dst_lbl))

    print_matrix_and_summary(results_matrix, src_labels, dst_labels, allowed_set)

    print("\n=== Cleanup ===")
    for ns in NAMESPACES:
        for idx in range(1, PODS_PER_NS + 1):
            delete_test_pod(ns, podname(ns, idx))

    print("\n=== Edge case summary ===")
    print("- DNS works only if there is an egress DNS exception")
    print("- No dev <-> prod, prod <-> dev, monitoring <-> prod etc. communication (zero trust)")
    print("- Intra-namespace communication (dev <-> dev, etc.) as per policies")
    print("- If you want to allow ping, you must allow ICMP in your NetworkPolicies")

if __name__ == "__main__":
    main()
