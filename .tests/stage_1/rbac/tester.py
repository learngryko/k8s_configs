import subprocess

# Test cases
tests = [
    # user-viewer
    ("user-viewer", "dev", "get pods", True),
    ("user-viewer", "dev", "list services", True),
    ("user-viewer", "dev", "watch configmaps", True),
    ("user-viewer", "dev", "create configmaps", False),
    ("user-viewer", "dev", "delete pods", False),
    ("user-viewer", "dev", "get secrets", False),
    ("user-viewer", "prod", "get pods", True),

    # user-dev
    ("user-dev", "dev", "create deployments", True),
    ("user-dev", "dev", "delete configmaps", True),
    ("user-dev", "dev", "create pods/exec", True), 
    ("user-dev", "dev", "create role", False),
    ("user-dev", "dev", "get secrets", True),
    ("user-dev", "prod", "create deployments", False), 

    # user-ops
    ("user-ops", "dev", "delete pods", True),
    ("user-ops", "dev", "create rolebindings", True),
    ("user-ops", "dev", "get secrets", True),
    ("user-ops", "dev", "create pods/exec", True),
    ("user-ops", "dev", "* *", True),
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
    for test in tests:
        run_test(*test)
