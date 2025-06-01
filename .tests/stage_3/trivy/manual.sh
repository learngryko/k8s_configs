#!/bin/bash

set -e

echo "🔁 Triggering manual vulnerability scans for all supported workloads..."
echo

# Workload types Trivy scans by owner
kinds=("replicaset" "statefulset" "daemonset" "cronjob" "job")

for kind in "${kinds[@]}"; do
  echo "📦 Scanning all $kind workloads..."
  kubectl get "$kind" -A -o custom-columns=NAMESPACE:.metadata.namespace,NAME:.metadata.name --no-headers | \
  while read ns name; do
    echo " → Annotating $kind $ns/$name"
    kubectl annotate "$kind" "$name" -n "$ns" \
      trivy-operator.aquasecurity.github.io/scan-trigger=manual --overwrite >/dev/null || true
  done
done

echo
echo "✅ Manual scan trigger completed. Wait 1–2 minutes and check reports with:"
echo "   kubectl get vulnerabilityreports -A"
