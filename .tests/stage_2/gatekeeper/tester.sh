#!/bin/bash

# Test: Pod z niezatwierdzonego rejestru
echo "Test 1: Niezatwierdzony rejestr"
kubectl apply -f - <<EOF
apiVersion: v1
kind: Pod
metadata:
  name: test-unapproved-registry
spec:
  containers:
    - name: test
      image: quay.io/invalid/image
      command: ["sleep", "3600"]
EOF

# Test: Pod z hostPath volume
echo "Test 2: hostPath volume"
kubectl apply -f - <<EOF
apiVersion: v1
kind: Pod
metadata:
  name: test-hostpath
spec:
  containers:
    - name: test
      image: docker.io/library/busybox
      command: ["sleep", "3600"]
      volumeMounts:
        - name: hostpath-vol
          mountPath: /host
  volumes:
    - name: hostpath-vol
      hostPath:
        path: /etc
EOF

# Test: Brak resource limits
echo "Test 3: Brak resources"
kubectl apply -f - <<EOF
apiVersion: v1
kind: Pod
metadata:
  name: test-no-resources
spec:
  containers:
    - name: test
      image: docker.io/library/busybox
      command: ["sleep", "3600"]
EOF

# Test: Brak readonlyRootFilesystem
echo "Test 4: Bez readOnlyRootFilesystem"
kubectl apply -f - <<EOF
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
      command: ["sleep", "3600"]
EOF

# Test: automountServiceAccountToken włączone
echo "Test 5: automountServiceAccountToken"
kubectl apply -f - <<EOF
apiVersion: v1
kind: Pod
metadata:
  name: test-serviceaccount-token
spec:
  automountServiceAccountToken: true
  containers:
    - name: test
      image: docker.io/library/busybox
      command: ["sleep", "3600"]
EOF
