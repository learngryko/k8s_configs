import subprocess
import sys
import time

NAMESPACES = ["dev", "prod", "monitoring"]
POD_IMAGE = "busybox:1.35.0"
TEST_DOMAIN = "google.com"
PODS_PER_NS = 2

def run(cmd):
    try:
        out = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT, timeout=30)
        return out.decode()
    except subprocess.CalledProcessError as e:
        return e.output.decode()
    except Exception as ex:
        return str(ex)

def create_test_pod(namespace, podname):
    print(f"Tworzę testowego poda: {podname} w ns {namespace}")
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
    # Czekaj aż pod będzie Running
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
    print(f"[ERROR] Pod {podname} nie wystartował w ns {namespace}")
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
    print(f"[DEBUG] exec {namespace}/{podname}: {cmd} => {repr(result)}")
    return result

def test_dns(namespace, podname):
    print(f"Testuję DNS w {namespace} ({podname}) ... ", end="")
    res = exec_pod(namespace, podname, f"nslookup {TEST_DOMAIN}")
    if "Name:" in res or "name =" in res:
        print("✅ DNS OK")
        return True
    else:
        print("❌ DNS BLOCKED")
        return False

def test_nc(src_ns, src_pod, dst_ip, port):
    res = exec_pod(src_ns, src_pod, f"nc -vz -w 2 {dst_ip} {port}")
    if "open" in res or "succeeded" in res:
        return True
    return False

def main():
    pods = {}  # {ns: [pod1, pod2]}
    pod_ips = {}  # {(ns, podname): ip}

    print("=== Tworzenie podów testowych ===")
    for ns in NAMESPACES:
        pods[ns] = []
        for idx in range(1, PODS_PER_NS + 1):
            podname = f"test-pod-{idx}-{ns}"
            if create_test_pod(ns, podname):
                pods[ns].append(podname)
            else:
                print(f"[FATAL] Nie można stworzyć poda {podname}. Przerwano.")
                sys.exit(1)

    print("Czekam 5 sekund na stabilizację sieci i DNS...")
    time.sleep(5)

    print("\n=== Testy DNS ===")
    for ns in NAMESPACES:
        for podname in pods[ns]:
            test_dns(ns, podname)
            pod_ips[(ns, podname)] = get_pod_ip(ns, podname)

    print("\n=== Connectivity matrix (nc 80) ===")
    for src_ns in NAMESPACES:
        for src_pod in pods[src_ns]:
            for dst_ns in NAMESPACES:
                for dst_pod in pods[dst_ns]:
                    dst_ip = pod_ips[(dst_ns, dst_pod)]
                    print(f"{src_ns}/{src_pod} -> {dst_ns}/{dst_pod}: ", end="")
                    ok_nc = test_nc(src_ns, src_pod, dst_ip, 80)
                    if ok_nc:
                        print("❌ ALLOWED (powinno być BLOCKED jeśli nie wyjątek)")
                    else:
                        print("✅ BLOCKED")

    print("\n=== Test DEV -> MONITORING (edge case: egress monitoring, port 3100) ===")
    dev_pod = pods["dev"][0]
    mon_pod = pods["monitoring"][0]
    mon_ip = pod_ips[("monitoring", mon_pod)]
    ok_nc = test_nc("dev", dev_pod, mon_ip, 3100)
    print(f"dev -> monitoring: ", end="")
    if ok_nc:
        print("✅ ALLOWED (OK, wyjątek monitoring działa)")
    else:
        print("❌ BLOCKED (powinno być ALLOWED)")

    print("\n=== Sprzątanie ===")
    for ns, podlist in pods.items():
        for pod in podlist:
            delete_test_pod(ns, pod)

    print("\n=== Podsumowanie edge-casów ===")
    print("- DNS działa tylko jeśli wyjątek egress DNS")
    print("- dev -> monitoring: musi być ALLOWED jeśli jest allow-egress-to-monitoring")
    print("- brak komunikacji dev <-> prod, prod <-> dev, monitoring <-> prod itd. (zero trust)")
    print("- komunikacja w ramach ns (dev <-> dev itd) zgodnie z politykami")

if __name__ == "__main__":
    main()
