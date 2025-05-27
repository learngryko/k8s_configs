#!/bin/bash

NAMESPACES=("dev" "monitoring" "prod")

print_test() {
  echo -e "\n\033[1;34m[Test $1] $2 [$3]\033[0m"
}

apply_and_log() {
  local test_id="$1"
  local test_desc="$2"
  local namespace="$3"
  local manifest="$4"

  print_test "$test_id" "$test_desc" "$namespace"
  echo "$manifest" | kubectl apply -n "$namespace" -f - 2>&1 | tee /dev/stderr | grep -i "Error from server" >/dev/null \
    && echo -e "\033[0;32m✅ Oczekiwane: polityka zadziałała\033[0m" \
    || echo -e "\033[0;31m❌ Błąd: polityka nie zadziałała\033[0m"
}

for ns in "${NAMESPACES[@]}"; do
  kubectl get ns "$ns" >/dev/null 2>&1 || kubectl create ns "$ns"

  apply_and_log "1" "Niezatwierdzony rejestr" "$ns" "
apiVersion: v1
kind: Pod
metadata:
  name: test-unapproved-registry
spec:
  containers:
    - name: test
      image: quay.io/invalid/image
      command: [\"sleep\", \"3600\"]
"

  apply_and_log "2" "hostPath volume" "$ns" "
apiVersion: v1
kind: Pod
metadata:
  name: test-hostpath
spec:
  containers:
    - name: test
      image: docker.io/library/busybox
      command: [\"sleep\", \"3600\"]
      volumeMounts:
        - name: hostpath-vol
          mountPath: /host
  volumes:
    - name: hostpath-vol
      hostPath:
        path: /etc
"

  apply_and_log "3" "Brak resource requests/limits" "$ns" "
apiVersion: v1
kind: Pod
metadata:
  name: test-no-resources
spec:
  containers:
    - name: test
      image: docker.io/library/busybox
      command: [\"sleep\", \"3600\"]
"

  apply_and_log "4" "readOnlyRootFilesystem = false" "$ns" "
apiVersion: v1
kind: Pod
metadata:
  name: test-readonly-false
spec:
  containers:
    - name: test
      image: docker.io/library/busybox
      securityContext:
        readOnlyRootFilesystem: false
      command: [\"sleep\", \"3600\"]
"

  apply_and_log "5" "automountServiceAccountToken = true" "$ns" "
apiVersion: v1
kind: Pod
metadata:
  name: test-serviceaccount-token
spec:
  automountServiceAccountToken: true
  containers:
    - name: test
      image: docker.io/library/busybox
      command: [\"sleep\", \"3600\"]
"
done
