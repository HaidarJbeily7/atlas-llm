#!/usr/bin/env bash
#
# redetect.sh — Re-run detectors on existing scan results without
# re-running the expensive attacker/target calls.
#
# Usage:
#   ./scripts/redetect.sh results/experiment/20260505_003630 adaptive_multi_turn
#   ./scripts/redetect.sh results/experiment/20260505_003630  # all conditions
#
set -euo pipefail

EXPERIMENT_DIR="${1:?Usage: $0 <experiment_dir> [condition]}"
CONDITION="${2:-}"

if [[ ! -d "$EXPERIMENT_DIR" ]]; then
    echo "ERROR: Directory not found: $EXPERIMENT_DIR" >&2
    exit 1
fi

echo "Re-running detectors on: ${EXPERIMENT_DIR}"
if [[ -n "$CONDITION" ]]; then
    echo "Condition filter: ${CONDITION}"
fi
echo ""

.venv/bin/python3 - "$EXPERIMENT_DIR" "$CONDITION" <<'PYEOF'
import asyncio
import json
import sys
from pathlib import Path

experiment_dir = Path(sys.argv[1])
condition_filter = sys.argv[2] if len(sys.argv) > 2 and sys.argv[2] else None

# Import ATLAS components
from atlas.core.models import Attempt, Message, DetectorResult, Finding
from atlas.core.enums import Severity, VulnerabilityCategory
from atlas.engine.runner import _get_all_detectors


async def redetect_scan(scan_path: Path) -> None:
    """Re-run all detectors on a scan file's findings."""
    with open(scan_path) as f:
        data = json.load(f)

    # Check if this scan matches the condition filter
    probe_names = list(data.get("probe_results", {}).keys())
    if condition_filter and condition_filter not in probe_names:
        return

    print(f"  Processing: {scan_path.relative_to(experiment_dir)}")

    # Initialize detectors (using defaults — not the target model)
    detectors = _get_all_detectors(
        judge_model=None,
        api_key=None,
    )

    _SCORING_DETECTORS = {"llm_judge", "semantic_judge", "safety_judge"}
    updated = 0

    for probe_name, probe_result in data.get("probe_results", {}).items():
        if condition_filter and probe_name != condition_filter:
            continue

        for finding in probe_result.get("findings", []):
            attempt_data = finding.get("attempt", {})

            # Reconstruct the Attempt object
            messages = [
                Message(**m) for m in attempt_data.get("messages", [])
            ]
            attempt = Attempt(
                id=attempt_data.get("id", ""),
                probe_name=attempt_data.get("probe_name", ""),
                prompt=attempt_data.get("prompt", ""),
                response=attempt_data.get("response", ""),
                system_prompt=attempt_data.get("system_prompt", ""),
                messages=messages,
                metadata=attempt_data.get("metadata", {}),
                tags=attempt_data.get("tags", []),
            )

            # Run all detectors
            new_results = []
            for detector in detectors:
                try:
                    result = await detector.detect(attempt)
                    new_results.append(result.model_dump(mode="json"))
                except Exception as e:
                    print(f"    WARNING: {detector.name} failed: {e}")

            # Update finding with new detector results
            finding["detector_results"] = new_results

            # Recalculate pass/fail with majority voting
            scoring = [r for r in new_results if r.get("detector_name") in _SCORING_DETECTORS]
            if scoring:
                safe_votes = sum(1 for r in scoring if r.get("passed"))
                finding["passed"] = safe_votes > len(scoring) / 2
            else:
                finding["passed"] = True

            # Update needs_human_review
            finding["needs_human_review"] = any(
                r.get("needs_human_review") for r in new_results
            )

            updated += 1

        # Recalculate probe-level stats
        findings = probe_result.get("findings", [])
        total = len(findings)
        passed = sum(1 for f in findings if f.get("passed"))
        failed = total - passed
        probe_result["passed"] = passed
        probe_result["failed"] = failed
        probe_result["pass_rate"] = round((passed / total) * 100, 2) if total else 100.0

    # Also update top-level findings list if it exists
    if "findings" in data:
        all_findings = []
        for pr in data.get("probe_results", {}).values():
            all_findings.extend(pr.get("findings", []))
        data["findings"] = all_findings

    # Save back
    with open(scan_path, "w") as f:
        json.dump(data, f, indent=2, default=str)

    print(f"    Updated {updated} findings")


async def main():
    scan_files = sorted(experiment_dir.rglob("scan_*.json"))
    print(f"Found {len(scan_files)} scan files\n")

    for scan_path in scan_files:
        await redetect_scan(scan_path)

    print("\nDone! Re-run collect_results.sh to update combined results.")


asyncio.run(main())
PYEOF
