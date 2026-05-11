#!/usr/bin/env python3
"""Aggregate Best-of-K scan results: K variants per intent → 1 finding per intent.

For each model's best_of_k_st scan, groups the K=5 findings by intent_id
and produces a single aggregated finding per intent:

  - Attack succeeds (passed=False) if ANY of the K variants succeeded.
  - The representative finding uses the "best" variant: first successful
    attack if one exists, otherwise the first variant.
  - All K variants' prompts/responses are preserved in metadata for review.
  - Cost, tokens, and latency are summed across all K variants (total budget).

The aggregated scan is written alongside the original as
``scan_*_aggregated.json`` (original is not modified).

Usage:
    python scripts/aggregate_bok_findings.py docs/experiment/20260505_003630
    python scripts/aggregate_bok_findings.py docs/experiment/20260505_003630 --in-place
"""
from __future__ import annotations

import argparse
import copy
import json
import sys
from collections import defaultdict
from pathlib import Path


def aggregate_bok_scan(scan: dict) -> dict:
    """Collapse K variants per intent into 1 finding per intent."""
    findings = scan.get("findings", [])
    if not findings:
        return scan

    # Group by intent_id
    by_intent: dict[str, list[dict]] = defaultdict(list)
    for f in findings:
        intent_id = f.get("attempt", {}).get("metadata", {}).get("intent_id", "")
        by_intent[intent_id].append(f)

    aggregated_findings = []
    for intent_id in sorted(by_intent.keys()):
        variants = by_intent[intent_id]
        # Sort: failed (attack succeeded) first, then by variant_index
        variants.sort(key=lambda v: (
            v.get("passed", True),  # False (attack success) first
            v.get("attempt", {}).get("metadata", {}).get("variant_index", 0),
        ))

        # Pick the best: first successful attack, or first variant if all refused
        best = variants[0]
        any_attack_succeeded = any(not v["passed"] for v in variants)

        # Deep copy so we don't mutate the original
        agg = copy.deepcopy(best)

        # Set passed based on any-of-K rule
        agg["passed"] = not any_attack_succeeded

        # Update severity if attack succeeded
        if any_attack_succeeded and agg.get("severity") == "low":
            agg["severity"] = best.get("severity", "high")

        # Sum cost/tokens/latency across all K variants
        attempt = agg.get("attempt", {})
        attempt["cost_usd"] = sum(
            v.get("attempt", {}).get("cost_usd", 0) or 0 for v in variants
        )
        attempt["latency_ms"] = sum(
            v.get("attempt", {}).get("latency_ms", 0) or 0 for v in variants
        )
        attempt["target_tokens_in"] = sum(
            v.get("attempt", {}).get("target_tokens_in", 0) or 0 for v in variants
        )
        attempt["target_tokens_out"] = sum(
            v.get("attempt", {}).get("target_tokens_out", 0) or 0 for v in variants
        )
        attempt["num_target_calls"] = sum(
            v.get("attempt", {}).get("num_target_calls", 0) or 0 for v in variants
        )

        # Store all K variants in metadata for review
        meta = attempt.get("metadata", {})
        meta["bok_aggregated"] = True
        meta["bok_total_variants"] = len(variants)
        meta["bok_variants_failed"] = sum(1 for v in variants if not v["passed"])
        meta["bok_best_variant_index"] = best.get("attempt", {}).get("metadata", {}).get("variant_index", 0)
        meta["bok_all_variants"] = []
        for v in sorted(variants, key=lambda x: x.get("attempt", {}).get("metadata", {}).get("variant_index", 0)):
            v_attempt = v.get("attempt", {})
            v_meta = v_attempt.get("metadata", {})
            meta["bok_all_variants"].append({
                "variant_index": v_meta.get("variant_index", 0),
                "prompt": v_attempt.get("prompt", ""),
                "response": v_attempt.get("response", ""),
                "response_preview": v_attempt.get("response", "")[:500],
                "passed": v.get("passed", True),
                "detector_summary": [
                    {"name": d.get("detector_name", ""), "passed": d.get("passed", True), "score": d.get("score", 0)}
                    for d in v.get("detector_results", [])
                ],
            })

        attempt["metadata"] = meta
        agg["attempt"] = attempt

        aggregated_findings.append(agg)

    # Build new scan with aggregated findings
    new_scan = copy.deepcopy(scan)
    new_scan["findings"] = aggregated_findings

    # Update probe results summary
    n_passed = sum(1 for f in aggregated_findings if f["passed"])
    n_failed = len(aggregated_findings) - n_passed
    if "probe_results" in new_scan:
        pr = new_scan["probe_results"]
        if isinstance(pr, dict):
            for key, val in pr.items():
                if isinstance(val, dict) and val.get("probe_name") == "best_of_k_st":
                    val["total_attempts"] = len(aggregated_findings)
                    val["passed"] = n_passed
                    val["failed"] = n_failed
                    val["findings"] = aggregated_findings
        elif isinstance(pr, list):
            for val in pr:
                if isinstance(val, dict) and val.get("probe_name") == "best_of_k_st":
                    val["total_attempts"] = len(aggregated_findings)
                    val["passed"] = n_passed
                    val["failed"] = n_failed

    return new_scan


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Aggregate Best-of-K findings: K variants → 1 per intent",
    )
    parser.add_argument(
        "experiment_dir",
        type=Path,
        help="Path to experiment results directory",
    )
    parser.add_argument(
        "--in-place",
        action="store_true",
        help="Overwrite original scan files (default: write *_aggregated.json alongside)",
    )
    parser.add_argument(
        "--condition",
        default="best_of_k_st",
        help="Condition name to aggregate (default: best_of_k_st)",
    )
    args = parser.parse_args()

    if not args.experiment_dir.is_dir():
        print(f"ERROR: {args.experiment_dir} is not a directory", file=sys.stderr)
        sys.exit(1)

    # Find all BoK scan files
    bok_scans = sorted(args.experiment_dir.rglob(f"*/{args.condition}/scan_*.json"))
    # Exclude already-aggregated files
    bok_scans = [s for s in bok_scans if "_aggregated" not in s.name]

    if not bok_scans:
        print(f"No {args.condition} scan files found in {args.experiment_dir}")
        sys.exit(0)

    print(f"Found {len(bok_scans)} {args.condition} scans to aggregate")
    print()

    for scan_path in bok_scans:
        model_dir = scan_path.parent.parent.name
        with open(scan_path) as f:
            scan = json.load(f)

        n_original = len(scan.get("findings", []))
        new_scan = aggregate_bok_scan(scan)
        n_aggregated = len(new_scan.get("findings", []))

        # Count attack successes
        n_attack_success = sum(1 for f in new_scan["findings"] if not f["passed"])

        if args.in_place:
            output_path = scan_path
        else:
            output_path = scan_path.with_name(
                scan_path.stem + "_aggregated.json"
            )

        with open(output_path, "w") as f:
            json.dump(new_scan, f, indent=2, ensure_ascii=False)

        print(
            f"  {model_dir}: {n_original} variants → {n_aggregated} intents "
            f"(ASR: {n_attack_success}/{n_aggregated} = {n_attack_success/n_aggregated:.0%}) "
            f"→ {output_path.name}"
        )

    print()
    print("Done. Aggregated scans ready for seeding.")
    if not args.in_place:
        print(
            "NOTE: Use --in-place to overwrite originals, or seed from the "
            "*_aggregated.json files."
        )


if __name__ == "__main__":
    main()
