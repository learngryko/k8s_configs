#!/bin/bash

set -e

echo "🔍 Scanning all workloads for Trivy vulnerability reports..."
echo

# Maps to track seen workload reports, and per-namespace totals
declare -A seen
declare -A ns_total
declare -A ns_scanned

total=0
scanned=0

# Workload kinds Trivy is configured to scan
workloads=("pod" "replicaset" "deployment" "statefulset" "daemonset" "job" "cronjob")

for kind in "${workloads[@]}"; do
  # List all workloads of this kind across all namespaces
  mapfile -t objects < <(kubectl get "$kind" -A -o custom-columns=NAMESPACE:.metadata.namespace,NAME:.metadata.name --no-headers)

  for entry in "${objects[@]}"; do
    ns=$(awk '{print $1}' <<< "$entry")
    name=$(awk '{print $2}' <<< "$entry")
    total=$((total+1))
    ns_total["$ns"]=$((ns_total["$ns"]+1))

    # Fetch reports that match the ownerReference (e.g. pod -> replicaset)
    reports=$(kubectl get vulnerabilityreports -n "$ns" -o json | jq -r --arg name "$name" --arg kind "$kind" '
      .items[] |
      select(.metadata.ownerReferences[]? as $owner |
        ($owner.name == $name and ($owner.kind // "" | ascii_downcase) == $kind)
      ) | @base64')

    # If one or more reports found, count the workload as scanned
    if [[ -n "$reports" ]]; then
      scanned=$((scanned+1))
      ns_scanned["$ns"]=$((ns_scanned["$ns"]+1))

      while IFS= read -r report_enc; do
        report=$(echo "$report_enc" | base64 -d)
        rname=$(echo "$report" | jq -r '.metadata.name')
        crit=$(echo "$report" | jq '.report.summary.criticalCount')
        high=$(echo "$report" | jq '.report.summary.highCount')
        med=$(echo "$report" | jq '.report.summary.mediumCount')
        low=$(echo "$report" | jq '.report.summary.lowCount')

        key="$ns/$name"
        # Print details only once per workload
        if [[ -z "${seen[$key]}" ]]; then
          seen[$key]=1
          echo "[$ns/$name] ($kind) → Report: $rname"
          echo "   Critical: $crit  High: $high  Medium: $med  Low: $low"
          echo "   View: kubectl get vulnerabilityreport $rname -n $ns -o yaml"
          echo
        fi
      done <<< "$reports"
    fi
  done
done

echo "✅ Cluster-wide scan coverage: $scanned / $total workloads"
echo
echo "📊 Per-namespace scan summary:"
printf "%-30s %10s %10s %10s\n" "Namespace" "Total" "Scanned" "Coverage"
for ns in "${!ns_total[@]}"; do
  total_ns=${ns_total[$ns]}
  scanned_ns=${ns_scanned[$ns]:-0}
  coverage=$(( 100 * scanned_ns / total_ns ))
  printf "%-30s %10d %10d %9d%%\n" "$ns" "$total_ns" "$scanned_ns" "$coverage"
done
