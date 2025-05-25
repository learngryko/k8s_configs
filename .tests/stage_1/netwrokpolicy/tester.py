import subprocess
import sys
import time

NAMESPACES = ["dev", "prod", "monitoring"]
POD_IMAGE = "busybox:1.35.0"  # stabilny, ma shelle i ping
TEST_DOMAIN = "google.com"

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
      image: alpine:3.18
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

    # Zapisz do tymczasowego pliku
    with open(f"/tmp/{podname}.yaml", "w") as f:
        f.write(pod_yaml)
    run(f"kubectl -n {namespace} apply -f /tmp/{podname}.yaml")
    # Czekaj aż będzie Running
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
    return run(f"kubectl -n {namespace} exec {podname} -- {cmd}")

def test_dns(namespace, podname):
    print(f"Testuję DNS w {namespace} ({podname}) ... ", end="")
    res = exec_pod(namespace, podname, f"nslookup {TEST_DOMAIN}")
    if "Name:" in res:
        print("✅ DNS OK")
        return True
    else:
        print("❌ DNS BLOCKED")
        return False

def test_ping(src_ns, src_pod, dst_ip):
    res = exec_pod(src_ns, src_pod, f"ping -c 2 -W 2 {dst_ip}")
    if "2 packets transmitted, 2 packets received" in res or "0% packet loss" in res:
        return True
    return False

def test_nc(src_ns, src_pod, dst_ip, port):
    res = exec_pod(src_ns, src_pod, f"nc -vz -w 2 {dst_ip} {port}")
    if "succeeded" in res or "open" in res:
        return True
    return False

def main():
    pods = {}

    print("=== Tworzenie podów testowych ===")
    for ns in NAMESPACES:
        podname = f"test-pod-{ns}"
        if create_test_pod(ns, podname):
            pods[ns] = podname
        else:
            print(f"[FATAL] Nie można stworzyć podów testowych. Przerwano.")
            sys.exit(1)

    print("\n=== Testy DNS ===")
    for ns in NAMESPACES:
        test_dns(ns, pods[ns])

    print("\n=== Connectivity matrix (ping/nc 80) ===")
    matrix = {}
    for src_ns in NAMESPACES:
        for dst_ns in NAMESPACES:
            src_pod = pods[src_ns]
            dst_pod = pods[dst_ns]
            dst_ip = get_pod_ip(dst_ns, dst_pod)
            print(f"{src_ns} -> {dst_ns}: ", end="")
            ok_ping = test_ping(src_ns, src_pod, dst_ip)
            ok_nc = test_nc(src_ns, src_pod, dst_ip, 80)
            if ok_ping or ok_nc:
                print("❌ ALLOWED (powinno być BLOCKED jeśli nie wyjątek)")
                matrix[(src_ns, dst_ns)] = "ALLOWED"
            else:
                print("✅ BLOCKED")
                matrix[(src_ns, dst_ns)] = "BLOCKED"

    print("\n=== Test DEV -> MONITORING (edge case: egress monitoring) ===")
    dev_pod = pods["dev"]
    mon_pod = pods["monitoring"]
    mon_ip = get_pod_ip("monitoring", mon_pod)
    ok_nc = test_nc("dev", dev_pod, mon_ip, 3100)  # Przykładowy port Loki
    print(f"dev -> monitoring: ", end="")
    if ok_nc:
        print("✅ ALLOWED (OK, wyjątek monitoring działa)")
    else:
        print("❌ BLOCKED (powinno być ALLOWED)")

    print("\n=== Sprzątanie ===")
    for ns, pod in pods.items():
        delete_test_pod(ns, pod)

    print("\n=== Podsumowanie edge-casów ===")
    print("- DNS działa tylko jeśli wyjątek egress DNS")
    print("- dev -> monitoring: musi być ALLOWED jeśli jest allow-egress-to-monitoring")
    print("- brak komunikacji dev <-> prod, prod <-> dev, monitoring <-> prod itd. (zero trust)")

if __name__ == "__main__":
    main()
