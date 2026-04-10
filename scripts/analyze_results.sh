#!/usr/bin/env bash
#
# analyze_results.sh — Compute key experiment metrics:
#   RQ1: ASR by condition, cost-effectiveness, effect sizes
#   RQ2: Failure-type distributions
#   RQ3: Detector agreement / sensitivity
#
# Usage:
#   ./scripts/analyze_results.sh results/experiment/20260406_130000
#
set -euo pipefail

EXPERIMENT_DIR="${1:?Usage: $0 <experiment_dir>}"
COMBINED="${EXPERIMENT_DIR}/combined_results.json"
ANALYSIS_DIR="${EXPERIMENT_DIR}/analysis"

if [[ ! -f "$COMBINED" ]]; then
    echo "ERROR: Run collect_results.sh first" >&2
    exit 1
fi

mkdir -p "$ANALYSIS_DIR"

echo "Analyzing results from: ${EXPERIMENT_DIR}"
echo ""

.venv/bin/python3 - "$COMBINED" "$ANALYSIS_DIR" <<'PYEOF'
import json
import math
import sys
from collections import Counter
from pathlib import Path

combined_path = Path(sys.argv[1])
analysis_dir = Path(sys.argv[2])

with open(combined_path) as f:
    data = json.load(f)

findings = data["findings"]
summaries = data["scan_summaries"]

if not findings:
    print("No findings to analyze.")
    sys.exit(0)

# ===================================================================
# RQ1: Attack Success Rate (ASR) by condition & model
# ===================================================================

print("=" * 60)
print("  RQ1: Attack Success Rate & Cost Analysis")
print("=" * 60)

# Group by (condition, model)
groups = {}
for f in findings:
    key = (f.get("condition", "?"), f.get("model", "?"))
    groups.setdefault(key, []).append(f)

# ASR table
print("\n--- ASR by Condition x Model ---\n")
print(f"{'Condition':<30s} {'Model':<25s} {'N':>5s} {'Fail':>5s} {'ASR%':>7s} {'Cost$':>10s} {'Tok/att':>8s}")
print("-" * 95)

condition_agg = {}
for (cond, model), rows in sorted(groups.items()):
    total = len(rows)
    failed = sum(1 for r in rows if not r["passed"])
    asr = (failed / total * 100) if total else 0
    cost = sum(r.get("cost_usd", 0) for r in rows)
    tokens = sum(r.get("target_tokens_in", 0) + r.get("target_tokens_out", 0)
                 + r.get("attacker_tokens_in", 0) + r.get("attacker_tokens_out", 0)
                 for r in rows)
    tok_per_att = tokens / total if total else 0

    print(f"{cond:<30s} {model:<25s} {total:5d} {failed:5d} {asr:6.1f}% ${cost:9.6f} {tok_per_att:8.0f}")

    # Aggregate by condition
    condition_agg.setdefault(cond, {"total": 0, "failed": 0, "cost": 0, "tokens": 0})
    condition_agg[cond]["total"] += total
    condition_agg[cond]["failed"] += failed
    condition_agg[cond]["cost"] += cost
    condition_agg[cond]["tokens"] += tokens

print("\n--- ASR by Condition (aggregated across models) ---\n")
print(f"{'Condition':<30s} {'N':>5s} {'Fail':>5s} {'ASR%':>7s} {'Total$':>11s} {'ASR/$':>9s}")
print("-" * 75)
for cond, agg in sorted(condition_agg.items()):
    asr = (agg["failed"] / agg["total"] * 100) if agg["total"] else 0
    asr_per_dollar = (agg["failed"] / agg["cost"]) if agg["cost"] > 0 else float("inf")
    print(f"{cond:<30s} {agg['total']:5d} {agg['failed']:5d} {asr:6.1f}% ${agg['cost']:10.6f} {asr_per_dollar:8.1f}")

# ===================================================================
# RQ2: Failure-Type Distribution
# ===================================================================

print("\n" + "=" * 60)
print("  RQ2: Failure-Type Distribution")
print("=" * 60)

# Collect failure types from LLM judge results
for detector_key in ["det_llm_judge_failure_type", "det_semantic_judge_failure_type"]:
    det_name = detector_key.replace("det_", "").replace("_failure_type", "")
    print(f"\n--- {det_name} failure types by condition ---\n")

    for cond in sorted(condition_agg.keys()):
        cond_findings = [f for f in findings if f.get("condition") == cond]
        types = Counter(f.get(detector_key, "") for f in cond_findings if f.get(detector_key))
        if types:
            print(f"  {cond}:")
            for t, count in types.most_common():
                pct = count / len(cond_findings) * 100
                print(f"    {t:<30s} {count:4d}  ({pct:.1f}%)")

# ===================================================================
# RQ3: Detector Agreement / Sensitivity
# ===================================================================

print("\n" + "=" * 60)
print("  RQ3: Detector Sensitivity")
print("=" * 60)

# Which detector fields exist?
det_names = set()
for f in findings:
    for k in f:
        if k.startswith("det_") and k.endswith("_passed"):
            det_names.add(k.replace("det_", "").replace("_passed", ""))

det_names = sorted(det_names)

if det_names:
    print(f"\nDetectors found: {', '.join(det_names)}")

    print(f"\n--- Detection rates (% of attempts flagged as UNSAFE) ---\n")
    print(f"{'Condition':<30s}", end="")
    for d in det_names:
        print(f" {d:>15s}", end="")
    print()
    print("-" * (30 + 16 * len(det_names)))

    for cond in sorted(condition_agg.keys()):
        cond_findings = [f for f in findings if f.get("condition") == cond]
        n = len(cond_findings)
        print(f"{cond:<30s}", end="")
        for d in det_names:
            key = f"det_{d}_passed"
            flagged = sum(1 for f in cond_findings if f.get(key) is False)
            rate = (flagged / n * 100) if n else 0
            print(f" {rate:14.1f}%", end="")
        print()

    # Pairwise agreement
    print(f"\n--- Pairwise detector agreement (% same verdict) ---\n")
    for i, d1 in enumerate(det_names):
        for d2 in det_names[i + 1:]:
            k1 = f"det_{d1}_passed"
            k2 = f"det_{d2}_passed"
            both_present = [f for f in findings if k1 in f and k2 in f
                           and f[k1] != "" and f[k2] != ""]
            if both_present:
                agree = sum(1 for f in both_present if f[k1] == f[k2])
                pct = agree / len(both_present) * 100
                print(f"  {d1} vs {d2}: {agree}/{len(both_present)} ({pct:.1f}%)")

# Needs-human-review stats
needs_review = sum(1 for f in findings if f.get("needs_human_review"))
print(f"\n--- Human Review ---")
print(f"  Findings flagged for review: {needs_review}/{len(findings)} ({needs_review/len(findings)*100:.1f}%)")

# ===================================================================
# Save analysis
# ===================================================================

analysis = {
    "total_findings": len(findings),
    "conditions": {
        cond: {
            "total": agg["total"],
            "failed": agg["failed"],
            "asr": (agg["failed"] / agg["total"] * 100) if agg["total"] else 0,
            "cost_usd": agg["cost"],
            "tokens": agg["tokens"],
        }
        for cond, agg in condition_agg.items()
    },
    "detector_names": det_names,
    "needs_human_review": needs_review,
}

with open(analysis_dir / "analysis_summary.json", "w") as f:
    json.dump(analysis, f, indent=2)

print(f"\nAnalysis saved to: {analysis_dir}/analysis_summary.json")
PYEOF
