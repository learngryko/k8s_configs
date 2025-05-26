import subprocess
import sys
import time
import concurrent.futures

NAMESPACES = ["dev", "prod", "monitoring"]
POD_IMAGE = "nicolaka/netshoot:latest"
TEST_DOMAIN = "google.com"
PODS_PER_NS = 2
NC_TIMEOUT = 10
DEBUG_LOG_FILE = "debug.log"

def short_name(ns, idx):
    return f"{ns}-{idx}"

def podname(ns, idx):
    return f"test-pod-{idx}-{ns}"

def run(cmd):
    # Run a shell command and return output as string
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
    # Each pod runs a TCP server on port 80 for connectivity tests
    pod_yaml = f"""
apiVersion: v1
kind: Pod
metadata:
  name: {podname}
spec:
  containers:
    - name: test
      image: {POD_IMAGE}
      command: ["/bin/sh", "-c", "while true; do nc -l -p 80 -e /bin/cat; done"]
      securityContext:
        runAsUser: 1000
        allowPrivilegeEscalation: false
        capabilities:
          drop: ["ALL"]
        runAsNonRoot: true
        seccompProfile:
          type: RuntimeDefault
  securityContext:
    runAsNonRoot: true
"""
    with open(f"/tmp/{podname}.yaml", "w") as f:
        f.write(pod_yaml)
    run(f"kubectl -n {namespace} apply -f /tmp/{podname}.yaml")
    # Wait until pod is Running
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
    # Execute a command in a pod and log to file only.
    full_cmd = f"kubectl -n {namespace} exec {podname} -- {cmd}"
    result = run(full_cmd)
    with open(DEBUG_LOG_FILE, "a") as dbg:
        dbg.write(f"[DEBUG] exec {namespace}/{podname}: {cmd} => {repr(result)}\n")
    return result

def test_dns(namespace, podname):
    print(f"Testing DNS in {namespace} ({podname}) ... ", end="")
    res = exec_pod(namespace, podname, f"nslookup {TEST_DOMAIN}")
    if "Name:" in res or "name =" in res:
        print("✅ DNS OK")
        return True
    else:
        print("❌ DNS BLOCKED")
        return False

def test_nc(src_ns, src_idx, dst_ns, dst_idx, dst_ip, port):
    src_pod = podname(src_ns, src_idx)
    dst_pod = podname(dst_ns, dst_idx)
    res = exec_pod(src_ns, src_pod, f"nc -vz -w {NC_TIMEOUT} {dst_ip} {port}")
    allowed = "open" in res or "succeeded" in res
    return allowed

def print_matrix_and_summary(results, src_labels, dst_labels, allowed_set):
    # Print header
    cell_width = 10
    print("\n=== Network Policy Matrix (nc 80) ===")
    print(" " * (max(len(s) for s in src_labels) + 1), end="")
    for dst in dst_labels:
        print(dst.ljust(cell_width), end="")
    print()
    # Print each row
    for i, src in enumerate(src_labels):
        print(src.ljust(max(len(s) for s in src_labels) + 1), end="")
        for j, dst in enumerate(dst_labels):
            cell = "ALLOWED" if results[i][j] else "BLOCKED"
            print(cell.ljust(cell_width), end="")
        print()
    # Summarize
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

    # Prepare pod structures
    pod_ips = {}  # (ns, idx) -> ip
    src_labels = []
    dst_labels = []

    print("=== Creating test pods ===")
    for ns in NAMESPACES:
        for idx in range(1, PODS_PER_NS + 1):
            p_name = podname(ns, idx)
            if create_test_pod(ns, p_name):
                pass
            else:
                print(f"[FATAL] Cannot create pod {p_name}. Aborting.")
                sys.exit(1)

    print("Waiting 5 seconds for network and DNS stabilization...")
    time.sleep(5)

    print("\n=== DNS Tests ===")
    for ns in NAMESPACES:
        for idx in range(1, PODS_PER_NS + 1):
            p_name = podname(ns, idx)
            test_dns(ns, p_name)
            pod_ips[(ns, idx)] = get_pod_ip(ns, p_name)
            lbl = short_name(ns, idx)
            if lbl not in src_labels:
                src_labels.append(lbl)
            if lbl not in dst_labels:
                dst_labels.append(lbl)

    # Matrix test cases
    results = []
    allowed_set = set()
    print("\n=== Connectivity matrix (nc 80, parallel) ===")
    # Prepare input for parallel
    test_cases = []
    for src_ns in NAMESPACES:
        for src_idx in range(1, PODS_PER_NS + 1):
            src_lbl = short_name(src_ns, src_idx)
            for dst_ns in NAMESPACES:
                for dst_idx in range(1, PODS_PER_NS + 1):
                    dst_lbl = short_name(dst_ns, dst_idx)
                    dst_ip = pod_ips[(dst_ns, dst_idx)]
                    test_cases.append( (src_ns, src_idx, dst_ns, dst_idx, dst_ip, 80, src_lbl, dst_lbl) )

    # Do parallel tests and collect results into matrix
    results_matrix = [[False for _ in dst_labels] for _ in src_labels]
    with concurrent.futures.ThreadPoolExecutor(max_workers=16) as executor:
        future_to_case = {
            executor.submit(test_nc, *args[:6]): args for args in test_cases
        }
        for future in concurrent.futures.as_completed(future_to_case):
            args = future_to_case[future]
            src_lbl = args[6]
            dst_lbl = args[7]
            i = src_labels.index(src_lbl)
            j = dst_labels.index(dst_lbl)
            allowed = future.result()
            results_matrix[i][j] = allowed
            if allowed and not (src_lbl == dst_lbl):  # skip self-test for now
                allowed_set.add((src_lbl, dst_lbl))

    print_matrix_and_summary(results_matrix, src_labels, dst_labels, allowed_set)

    print("\n=== Test DEV -> MONITORING (edge case: egress monitoring, port 3100) ===")
    dev_lbl = short_name("dev", 1)
    mon_lbl = short_name("monitoring", 1)
    dev_ip = pod_ips[("dev", 1)]
    mon_ip = pod_ips[("monitoring", 1)]
    allowed = test_nc("dev", 1, "monitoring", 1, mon_ip, 3100)
    edge_str = "ALLOWED" if allowed else "BLOCKED"
    print(f"{dev_lbl} -> {mon_lbl} (3100): {edge_str}")

    print("\n=== Cleanup ===")
    for ns in NAMESPACES:
        for idx in range(1, PODS_PER_NS + 1):
            delete_test_pod(ns, podname(ns, idx))

    print("\n=== Edge case summary ===")
    print("- DNS works only if there is an egress DNS exception")
    print("- dev -> monitoring: should be ALLOWED if allow-egress-to-monitoring is present")
    print("- no dev <-> prod, prod <-> dev, monitoring <-> prod etc. communication (zero trust)")
    print("- intra-namespace communication (dev <-> dev, etc.) as per policies")

if __name__ == "__main__":
    main()
