import subprocess
import sys

CAN_I_YAML = """
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: can-i-checker
rules:
- apiGroups: ["authorization.k8s.io"]
  resources: ["selfsubjectaccessreviews"]
  verbs: ["create"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: can-i-checker-binding
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: can-i-checker
subjects:
- kind: User
  name: user-viewer
- kind: User
  name: user-dev
- kind: User
  name: user-ops
"""

def apply_rbac():
    # apply the RBAC yaml for selfsubjectaccessreviews
    proc = subprocess.run(["kubectl", "apply", "-f", "-"], input=CAN_I_YAML.encode(), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if proc.returncode != 0:
        print("Failed to apply can-i RBAC:", proc.stderr.decode())
        sys.exit(2)

def delete_rbac():
    # delete temporary RBAC resources
    subprocess.run(["kubectl", "delete", "clusterrole", "can-i-checker"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    subprocess.run(["kubectl", "delete", "clusterrolebinding", "can-i-checker-binding"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

tests = [
    # user-viewer (read-only everywhere)
    ("user-viewer", "dev", "get pods", True),
    ("user-viewer", "dev", "list services", True),
    ("user-viewer", "dev", "watch configmaps", True),
    ("user-viewer", "dev", "create configmaps", False),
    ("user-viewer", "dev", "delete pods", False),
    ("user-viewer", "dev", "get secrets", False),
    ("user-viewer", "prod", "get pods", True),
    ("user-viewer", "prod", "get secrets", False),
    ("user-viewer", "monitoring", "list pods", True),
    ("user-viewer", "monitoring", "delete configmaps", False),
    ("user-viewer", "monitoring", "create pods/exec", False),
    ("user-viewer", "prod", "create rolebindings", False),

    # user-dev (full access to dev only)
    ("user-dev", "dev", "get pods", True),
    ("user-dev", "dev", "create deployments", True),
    ("user-dev", "dev", "create pods/exec", True),
    ("user-dev", "dev", "delete secrets", True),
    ("user-dev", "dev", "create jobs", True),
    ("user-dev", "dev", "patch pods", True),
    ("user-dev", "dev", "create role", False),
    ("user-dev", "dev", "create clusterrole", False),
    ("user-dev", "prod", "get pods", False),
    ("user-dev", "prod", "create secrets", False),
    ("user-dev", "monitoring", "list jobs", False),
    ("user-dev", "monitoring", "delete pods", False),

    # user-ops (admin everywhere)
    ("user-ops", "dev", "delete pods", True),
    ("user-ops", "dev", "create rolebindings", True),
    ("user-ops", "dev", "create pods/exec", True),
    ("user-ops", "dev", "create clusterrole", True),
    ("user-ops", "dev", "* *", True),
    ("user-ops", "prod", "delete secrets", True),
    ("user-ops", "prod", "create jobs", True),
    ("user-ops", "prod", "patch pods", True),
    ("user-ops", "monitoring", "delete pods", True),
    ("user-ops", "monitoring", "get secrets", True),
    ("user-ops", "monitoring", "create pods/exec", True),
    ("user-ops", "monitoring", "delete rolebindings", True),
]


def run_test(user, namespace, action, should_pass):
    cmd = ["kubectl", "auth", "can-i"] + action.split() + ["-n", namespace, "--as", user]
    try:
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=5)
        output = result.stdout.decode().strip()
        passed = output == "yes"
    except Exception as e:
        output = str(e)
        passed = False

    status = "✅ PASS" if passed == should_pass else "❌ FAIL"
    print(f"[{status}] {user} → {action} @ {namespace} (expected: {'yes' if should_pass else 'no'}) → got: {output}")

if __name__ == "__main__":
    print("🔍 RBAC Health Check\n--------------------")
    apply_rbac()
    try:
        for test in tests:
            run_test(*test)
    finally:
        delete_rbac()
