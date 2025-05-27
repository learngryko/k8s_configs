#!/bin/bash

NAMESPACE="default"
LOGFILE="tester.log"
OK=0
FAIL=0

declare -A SUMMARY

print_test() {
  echo -e "\n\033[1;34m$1\033[0m" | tee -a "$LOGFILE"
}

run_and_check() {
  local name="$1"
  local manifest="$2"
  local expect_fail="$3"

  print_test "Test: $name"
  output=$(echo "$manifest" | kubectl apply -n "$NAMESPACE" -f - 2>&1 | tee -a "$LOGFILE")
  if [[ $output =~ "Error from server" ]]; then
    if [[ "$expect_fail" == "yes" ]]; then
      echo -e "\033[0;32m✅ Oczekiwany błąd: polityka działa\033[0m" | tee -a "$LOGFILE"
      SUMMARY["$name"]="✅"
      ((OK++))
    else
      echo -e "\033[0;31m❌ NIEPOŻĄDANY błąd! $output\033[0m" | tee -a "$LOGFILE"
      SUMMARY["$name"]="❌"
      ((FAIL++))
    fi
  else
    if [[ "$expect_fail" == "yes" ]]; then
      echo -e "\033[0;31m❌ BRAK błędu: polityka NIE DZIAŁA\033[0m" | tee -a "$LOGFILE"
      SUMMARY["$name"]="❌"
      ((FAIL++))
    else
      echo -e "\033[0;32m✅ Pod utworzony prawidłowo\033[0m" | tee -a "$LOGFILE"
      SUMMARY["$name"]="✅"
      ((OK++))
    fi
  fi
}

# 1. Poprawny pod
GOOD_POD="
apiVersion: v1
kind: Pod
metadata:
  name: valid-pod
spec:
  automountServiceAccountToken: false
  containers:
    - name: test
      image: docker.io/library/busybox
      command: [\"sleep\", \"3600\"]
      resources:
        requests:
          cpu: \"10m\"
          memory: \"16Mi\"
        limits:
          cpu: \"100m\"
          memory: \"64Mi\"
      securityContext:
        readOnlyRootFilesystem: true
"
run_and_check "Poprawny Pod – powinien przejść" "$GOOD_POD" "no"

# 2. Zły rejestr
BAD_REGISTRY_POD="
apiVersion: v1
kind: Pod
metadata:
  name: invalid-registry
spec:
  automountServiceAccountToken: false
  containers:
    - name: test
      image: quay.io/invalid/image
      command: [\"sleep\", \"3600\"]
      resources:
        requests:
          cpu: \"10m\"
          memory: \"16Mi\"
        limits:
          cpu: \"100m\"
          memory: \"64Mi\"
      securityContext:
        readOnlyRootFilesystem: true
"
run_and_check "Niezatwierdzony rejestr" "$BAD_REGISTRY_POD" "yes"

# 3. hostPath
BAD_HOSTPATH_POD="
apiVersion: v1
kind: Pod
metadata:
  name: invalid-hostpath
spec:
  automountServiceAccountToken: false
  containers:
    - name: test
      image: docker.io/library/busybox
      command: [\"sleep\", \"3600\"]
      resources:
        requests:
          cpu: \"10m\"
          memory: \"16Mi\"
        limits:
          cpu: \"100m\"
          memory: \"64Mi\"
      securityContext:
        readOnlyRootFilesystem: true
      volumeMounts:
        - name: hostpath-vol
          mountPath: /host
  volumes:
    - name: hostpath-vol
      hostPath:
        path: /etc
"
run_and_check "hostPath" "$BAD_HOSTPATH_POD" "yes"

# 4. Brak resource limits
NO_RESOURCES_POD="
apiVersion: v1
kind: Pod
metadata:
  name: invalid-noresources
spec:
  automountServiceAccountToken: false
  containers:
    - name: test
      image: docker.io/library/busybox
      command: [\"sleep\", \"3600\"]
      securityContext:
        readOnlyRootFilesystem: true
"
run_and_check "Brak resource requests/limits" "$NO_RESOURCES_POD" "yes"

# 5. Brak readOnlyRootFilesystem
NO_READONLY_POD="
apiVersion: v1
kind: Pod
metadata:
  name: invalid-noreadonly
spec:
  automountServiceAccountToken: false
  containers:
    - name: test
      image: docker.io/library/busybox
      command: [\"sleep\", \"3600\"]
      resources:
        requests:
          cpu: \"10m\"
          memory: \"16Mi\"
        limits:
          cpu: \"100m\"
          memory: \"64Mi\"
"
run_and_check "Brak readOnlyRootFilesystem" "$NO_READONLY_POD" "yes"

# 6. automountServiceAccountToken włączone
BAD_AUTOMOUNT_POD="
apiVersion: v1
kind: Pod
metadata:
  name: invalid-automount
spec:
  automountServiceAccountToken: true
  containers:
    - name: test
      image: docker.io/library/busybox
      command: [\"sleep\", \"3600\"]
      resources:
        requests:
          cpu: \"10m\"
          memory: \"16Mi\"
        limits:
          cpu: \"100m\"
          memory: \"64Mi\"
      securityContext:
        readOnlyRootFilesystem: true
"
run_and_check "automountServiceAccountToken = true" "$BAD_AUTOMOUNT_POD" "yes"

# --- CLEANUP ---
print_test "Sprzątanie podów..."
kubectl delete pod valid-pod invalid-registry invalid-hostpath invalid-noresources invalid-noreadonly invalid-automount -n "$NAMESPACE" --wait=false >/dev/null 2>&1 | tee -a "$LOGFILE"

# --- SUMMARY ---
print_test "PODSUMOWANIE"
for k in "${!SUMMARY[@]}"; do
  echo -e "${SUMMARY[$k]}\t$k" | tee -a "$LOGFILE"
done
echo -e "\nRazem: \033[0;32m$OK OK\033[0m, \033[0;31m$FAIL błędów\033[0m" | tee -a "$LOGFILE"
