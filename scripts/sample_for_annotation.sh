#!/usr/bin/env bash
#
# sample_for_annotation.sh — Sample findings for human annotation.
#
# Produces a stratified sample (balanced across conditions and models)
# with all info needed for the annotation protocol (RQ2).
#
# Usage:
#   ./scripts/sample_for_annotation.sh results/experiment/20260406_130000
#   ./scripts/sample_for_annotation.sh results/experiment/20260406_130000 --n 200
#
set -euo pipefail

EXPERIMENT_DIR="${1:?Usage: $0 <experiment_dir> [--n SAMPLE_SIZE]}"
SAMPLE_SIZE=200

shift
while [[ $# -gt 0 ]]; do
    case "$1" in
        --n) SAMPLE_SIZE="$2"; shift 2 ;;
        *) echo "Unknown: $1" >&2; exit 1 ;;
    esac
done

COMBINED="${EXPERIMENT_DIR}/combined_results.json"
OUTPUT="${EXPERIMENT_DIR}/annotation_sample.json"
OUTPUT_CSV="${EXPERIMENT_DIR}/annotation_sample.csv"

if [[ ! -f "$COMBINED" ]]; then
    echo "ERROR: Run collect_results.sh first (no combined_results.json found)" >&2
    exit 1
fi

echo "Sampling ${SAMPLE_SIZE} findings for human annotation..."

.venv/bin/python3 - "$COMBINED" "$OUTPUT" "$OUTPUT_CSV" "$SAMPLE_SIZE" <<'PYEOF'
import csv
import json
import random
import sys
from pathlib import Path

combined_path = Path(sys.argv[1])
output_json = Path(sys.argv[2])
output_csv = Path(sys.argv[3])
sample_size = int(sys.argv[4])

random.seed(42)  # Reproducible sampling

with open(combined_path) as f:
    data = json.load(f)

findings = data["findings"]
if not findings:
    print("No findings to sample.")
    sys.exit(0)

# Group by (condition, model) for stratified sampling
groups = {}
for f in findings:
    key = (f.get("condition", "unknown"), f.get("model", "unknown"))
    groups.setdefault(key, []).append(f)

# Compute per-group sample size (balanced)
num_groups = len(groups)
per_group = max(1, sample_size // num_groups)

sampled = []
for key, group_findings in sorted(groups.items()):
    n = min(per_group, len(group_findings))
    sampled.extend(random.sample(group_findings, n))

# If we haven't reached sample_size, fill from remaining
remaining = [f for f in findings if f not in sampled]
shortfall = sample_size - len(sampled)
if shortfall > 0 and remaining:
    sampled.extend(random.sample(remaining, min(shortfall, len(remaining))))

# Prepare annotation records with full context
annotation_records = []
for i, f in enumerate(sampled):
    record = {
        "annotation_id": i + 1,
        "finding_id": f.get("finding_id", ""),
        "model": f.get("model", ""),
        "condition": f.get("condition", ""),
        "adaptivity": f.get("adaptivity", ""),
        "interaction_mode": f.get("interaction_mode", ""),
        "intent_id": f.get("intent_id", ""),
        "probe": f.get("probe", ""),
        "prompt": f.get("prompt", ""),
        "response": f.get("response", ""),
        # Pre-filled automated results for comparison
        "auto_passed": f.get("passed", True),
        "auto_needs_review": f.get("needs_human_review", False),
        # Detector details
        "det_keyword_passed": f.get("det_keyword_passed", ""),
        "det_refusal_passed": f.get("det_refusal_passed", ""),
        "det_llm_judge_passed": f.get("det_llm_judge_passed", ""),
        "det_llm_judge_failure_type": f.get("det_llm_judge_failure_type", ""),
        "det_semantic_judge_passed": f.get("det_semantic_judge_passed", ""),
        "det_semantic_judge_failure_type": f.get("det_semantic_judge_failure_type", ""),
        # Human annotation fields (to be filled by annotators)
        "human_safe": "",           # TRUE / FALSE
        "human_failure_type": "",   # from taxonomy
        "human_severity": "",       # 1-5 scale
        "human_notes": "",
        "annotator_id": "",
    }
    annotation_records.append(record)

# Save JSON
with open(output_json, "w") as f:
    json.dump(annotation_records, f, indent=2, default=str)

# Save CSV
if annotation_records:
    keys = list(annotation_records[0].keys())
    with open(output_csv, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(annotation_records)

# Stats
conditions = {}
for r in annotation_records:
    c = r["condition"]
    conditions[c] = conditions.get(c, 0) + 1

print(f"Sampled {len(annotation_records)} findings (target: {sample_size})")
print(f"  JSON: {output_json}")
print(f"  CSV:  {output_csv}")
print(f"\nDistribution by condition:")
for c, n in sorted(conditions.items()):
    print(f"  {c:30s}  {n}")
print(f"\nDistribute the CSV to annotators. Human fields are blank for them to fill.")
PYEOF
