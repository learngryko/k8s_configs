import subprocess
import sys
import time
import concurrent.futures

NAMESPACES = ["dev", "prod", "monitoring"]
POD_IMAGE = "busybox:1.35.0"
TEST_DOMAIN = "google.com"
PODS_PER_NS = 2
NC_TIMEOUT = 10

DEBUG_LOG_FILE = "debug.log"

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
    # This pod runs a TCP server on port 80 for connectivity tests
    pod_yaml = f"""
apiVersion: v1
kind: Pod
metadata:
  name: {podname}
spec:
  containers:
    - name: test
      image: {POD_IMAGE}
      command: ["/bin/sh", "-c", "nc -lk -p 80 & sleep 3600"]
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
    for i in range(30):
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
    # Delete test pod at the end of testing
    run(f"kubectl -n {namespace} delete pod {podname} --ignore-not-found")

def get_pod_ip(namespace, podname):
    # Get pod IP address
    ip = run(f"kubectl -n {namespace} get pod {podname} -o=jsonpath='{{.status.podIP}}'")
    return ip.strip()

def exec_pod(namespace, podname, cmd):
    # Execute a command in a pod and return the result. Debug to file only.
    full_cmd = f"kubectl -n {namespace} exec {podname} -- {cmd}"
    result = run(full_cmd)
    with open(DEBUG_LOG_FILE, "a") as dbg:
        dbg.write(f"[DEBUG] exec {namespace}/{podname}: {cmd} => {repr(result)}\n")
    return result

def test_dns(namespace, podname):
    # Test DNS resolution inside the pod
    print(f"Testing DNS in {namespace} ({podname}) ... ", end="")
    res = exec_pod(namespace, podname, f"nslookup {TEST_DOMAIN}")
    if "Name:" in res or "name =" in res:
        print("✅ DNS OK")
        return True
    else:
        print("❌ DNS BLOCKED")
        return False

def test_nc(src_ns, src_pod, dst_ns, dst_pod, dst_ip, port):
    # Test TCP connectivity from one pod to another on a given port
    res = exec_pod(src_ns, src_pod, f"nc -vz -w {NC_TIMEOUT} {dst_ip} {port}")
    allowed = "open" in res or "succeeded" in res
    result = (
        f"{src_ns}/{src_pod} -> {dst_ns}/{dst_pod}: " +
        ("❌ ALLOWED (should be BLOCKED unless exception)" if allowed else "✅ BLOCKED")
    )
    return result

def main():
    # Clean old debug log at the start
    open(DEBUG_LOG_FILE, "w").close()

    pods = {}  # {ns: [pod1, pod2]}
    pod_ips = {}  # {(ns, podname): ip}

    print("=== Creating test pods ===")
    for ns in NAMESPACES:
        pods[ns] = []
        for idx in range(1, PODS_PER_NS + 1):
            podname = f"test-pod-{idx}-{ns}"
            if create_test_pod(ns, podname):
                pods[ns].append(podname)
            else:
                print(f"[FATAL] Cannot create pod {podname}. Aborting.")
                sys.exit(1)

    print("Waiting 5 seconds for network and DNS stabilization...")
    time.sleep(5)

    print("\n=== DNS Tests ===")
    for ns in NAMESPACES:
        for podname in pods[ns]:
            test_dns(ns, podname)
            pod_ips[(ns, podname)] = get_pod_ip(ns, podname)

    print("\n=== Connectivity matrix (nc 80, parallel) ===")
    test_cases = []
    for src_ns in NAMESPACES:
        for src_pod in pods[src_ns]:
            for dst_ns in NAMESPACES:
                for dst_pod in pods[dst_ns]:
                    dst_ip = pod_ips[(dst_ns, dst_pod)]
                    test_cases.append( (src_ns, src_pod, dst_ns, dst_pod, dst_ip, 80) )

    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=16) as executor:
        future_to_test = {
            executor.submit(test_nc, *args): args
            for args in test_cases
        }
        for future in concurrent.futures.as_completed(future_to_test):
            result = future.result()
            print(result)
            results.append(result)

    print("\n=== Test DEV -> MONITORING (edge case: egress monitoring, port 3100) ===")
    dev_pod = pods["dev"][0]
    mon_pod = pods["monitoring"][0]
    mon_ip = pod_ips[("monitoring", mon_pod)]
    edge_case = test_nc("dev", dev_pod, "monitoring", mon_pod, mon_ip, 3100)
    print(f"dev -> monitoring: {edge_case}")

    print("\n=== Cleanup ===")
    for ns, podlist in pods.items():
        for pod in podlist:
            delete_test_pod(ns, pod)

    print("\n=== Edge case summary ===")
    print("- DNS works only if there is an egress DNS exception")
    print("- dev -> monitoring: should be ALLOWED if allow-egress-to-monitoring is present")
    print("- no dev <-> prod, prod <-> dev, monitoring <-> prod etc. communication (zero trust)")
    print("- intra-namespace communication (dev <-> dev, etc.) as per policies")

if __name__ == "__main__":
    main()
