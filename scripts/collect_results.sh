#!/usr/bin/env bash
#
# collect_results.sh — Collect experiment results into a single CSV/JSON
# for analysis in R, Python, or any stats tool.
#
# Usage:
#   ./scripts/collect_results.sh results/experiment/20260406_130000
#
set -euo pipefail

EXPERIMENT_DIR="${1:?Usage: $0 <experiment_dir>}"

if [[ ! -d "$EXPERIMENT_DIR" ]]; then
    echo "ERROR: Directory not found: $EXPERIMENT_DIR" >&2
    exit 1
fi

OUTPUT_JSON="${EXPERIMENT_DIR}/combined_results.json"
OUTPUT_CSV="${EXPERIMENT_DIR}/combined_results.csv"

echo "Collecting results from: ${EXPERIMENT_DIR}"
echo ""

# ---------------------------------------------------------------------------
# Combine all scan JSON files into one array
# ---------------------------------------------------------------------------

.venv/bin/python3 - "$EXPERIMENT_DIR" "$OUTPUT_JSON" "$OUTPUT_CSV" <<'PYEOF'
import csv
import json
import sys
from pathlib import Path

experiment_dir = Path(sys.argv[1])
output_json = Path(sys.argv[2])
output_csv = Path(sys.argv[3])

all_findings = []
scan_summaries = []

for scan_file in sorted(experiment_dir.rglob("scan_*.json")):
    with open(scan_file) as f:
        data = json.load(f)

    model = data.get("model_name", "")
    scan_id = data.get("scan_id", "")
    total_cost = data.get("total_cost_usd", 0.0)
    total_target_tokens = data.get("total_target_tokens", 0)
    total_attacker_tokens = data.get("total_attacker_tokens", 0)

    # Scan-level summary
    for probe_name, probe_result in data.get("probe_results", {}).items():
        scan_summaries.append({
            "scan_id": scan_id,
            "model": model,
            "probe": probe_name,
            "total_attempts": probe_result.get("total_attempts", 0),
            "passed": probe_result.get("passed", 0),
            "failed": probe_result.get("failed", 0),
            "pass_rate": probe_result.get("pass_rate", 0.0),
            "total_cost_usd": total_cost,
            "total_target_tokens": total_target_tokens,
            "total_attacker_tokens": total_attacker_tokens,
        })

    # Finding-level detail
    for finding in data.get("findings", []):
        attempt = finding.get("attempt", {})
        meta = attempt.get("metadata", {})

        row = {
            "scan_id": scan_id,
            "model": model,
            "finding_id": finding.get("id", ""),
            "probe": attempt.get("probe_name", ""),
            "intent_id": meta.get("intent_id", ""),
            "condition": meta.get("condition", ""),
            "adaptivity": meta.get("adaptivity", ""),
            "interaction_mode": meta.get("interaction_mode", ""),
            "passed": finding.get("passed", True),
            "needs_human_review": finding.get("needs_human_review", False),
            "severity": finding.get("severity", ""),
            "prompt": attempt.get("prompt", "")[:200],
            "response": attempt.get("response", "")[:200],
            "target_tokens_in": attempt.get("target_tokens_in", 0),
            "target_tokens_out": attempt.get("target_tokens_out", 0),
            "attacker_tokens_in": attempt.get("attacker_tokens_in", 0),
            "attacker_tokens_out": attempt.get("attacker_tokens_out", 0),
            "cost_usd": attempt.get("cost_usd", 0.0),
            "latency_ms": attempt.get("latency_ms", 0.0),
            "num_target_calls": attempt.get("num_target_calls", 0),
            "num_attacker_calls": attempt.get("num_attacker_calls", 0),
        }

        # Error field from metadata
        row["error"] = meta.get("error", "")

        # LLM response metadata (finish_reason, model_id, token details)
        resp_meta = attempt.get("response_metadata", {})
        row["finish_reason"] = resp_meta.get("finish_reason", "")
        row["model_id"] = resp_meta.get("model_id", "")
        row["prompt_tokens"] = resp_meta.get("prompt_tokens", 0)
        row["completion_tokens"] = resp_meta.get("completion_tokens", 0)

        # Per-detector results (including costs and judge metadata)
        total_det_cost = 0.0
        for dr in finding.get("detector_results", []):
            name = dr.get("detector_name", "unknown")
            row[f"det_{name}_passed"] = dr.get("passed", True)
            row[f"det_{name}_score"] = dr.get("score", 0.0)
            row[f"det_{name}_confidence"] = dr.get("confidence", 0.0)
            row[f"det_{name}_failure_type"] = dr.get("failure_type", "")
            row[f"det_{name}_needs_review"] = dr.get("needs_human_review", False)
            # Judge cost and metadata
            row[f"det_{name}_judge_model"] = dr.get("judge_model", "")
            row[f"det_{name}_judge_tokens_in"] = dr.get("judge_tokens_in", 0)
            row[f"det_{name}_judge_tokens_out"] = dr.get("judge_tokens_out", 0)
            row[f"det_{name}_judge_cost_usd"] = dr.get("judge_cost_usd", 0.0)
            row[f"det_{name}_judge_latency_ms"] = dr.get("judge_latency_ms", 0.0)
            row[f"det_{name}_judge_reasoning"] = (dr.get("judge_reasoning", "") or "")[:500]
            row[f"det_{name}_dimension_scores"] = json.dumps(dr.get("dimension_scores", {}))
            total_det_cost += dr.get("judge_cost_usd", 0.0) or 0.0

        row["total_detector_cost_usd"] = total_det_cost
        row["total_cost_with_detectors_usd"] = (row.get("cost_usd", 0.0) or 0.0) + total_det_cost

        all_findings.append(row)

# Write combined JSON
combined = {
    "experiment_dir": str(experiment_dir),
    "total_findings": len(all_findings),
    "scan_summaries": scan_summaries,
    "findings": all_findings,
}
with open(output_json, "w") as f:
    json.dump(combined, f, indent=2, default=str)

# Write CSV
if all_findings:
    # Collect all possible columns
    all_keys = []
    seen = set()
    for row in all_findings:
        for k in row:
            if k not in seen:
                all_keys.append(k)
                seen.add(k)

    with open(output_csv, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=all_keys, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(all_findings)

print(f"Collected {len(all_findings)} findings from {len(scan_summaries)} probe runs")
print(f"  JSON: {output_json}")
print(f"  CSV:  {output_csv}")

# Quick stats
if all_findings:
    conditions = {}
    for row in all_findings:
        c = row.get("condition", "unknown")
        conditions.setdefault(c, {"total": 0, "failed": 0})
        conditions[c]["total"] += 1
        if not row["passed"]:
            conditions[c]["failed"] += 1

    print("\n--- Attack Success Rate (ASR) by Condition ---")
    for c, counts in sorted(conditions.items()):
        asr = (counts["failed"] / counts["total"] * 100) if counts["total"] else 0
        print(f"  {c:30s}  {counts['failed']:3d}/{counts['total']:3d}  ASR={asr:.1f}%")

    # Human review stats
    needs_review = sum(1 for r in all_findings if r.get("needs_human_review"))
    print(f"\nFindings needing human review: {needs_review}/{len(all_findings)}")
PYEOF

echo ""
echo "Done. Use the CSV for statistical analysis (R, pandas, etc.)"
