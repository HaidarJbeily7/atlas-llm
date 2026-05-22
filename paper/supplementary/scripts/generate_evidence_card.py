#!/usr/bin/env python3
"""Generate ATLAS Evidence Card with comprehensive per-condition metrics.

ASR numbers come from the annotation ledger (single source of truth).
Operational metrics (cost, latency, target calls, detector results) come
from experiment scan files, joined to the ledger by (model, intent_id, condition).

Usage:
    python3 scripts/generate_evidence_card.py
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
from collections import defaultdict
from pathlib import Path

EXPERIMENT_DIR = "docs/experiment/20260505_003630"
LEDGER_PATH = "docs/v6/artifacts/annotation_ledger.csv"


def wilson_ci(successes: int, n: int, z: float = 1.96) -> tuple[float, float, float]:
    """Wilson score interval for binomial proportion. Returns (point%, lower%, upper%)."""
    if n == 0:
        return (0.0, 0.0, 0.0)
    p_hat = successes / n
    denom = 1 + z**2 / n
    centre = (p_hat + z**2 / (2 * n)) / denom
    margin = z / denom * math.sqrt(p_hat * (1 - p_hat) / n + z**2 / (4 * n**2))
    return (
        round(p_hat * 100, 2),
        round(max(0.0, centre - margin) * 100, 2),
        round(min(1.0, centre + margin) * 100, 2),
    )


def load_ledger(ledger_path: Path) -> list[dict]:
    """Load annotation ledger CSV."""
    with open(ledger_path) as f:
        return list(csv.DictReader(f))


def load_operational_data(experiment_dir: Path) -> dict:
    """Load operational metrics from scan files.

    Returns dict keyed by (model, intent_id, condition) with cost, latency,
    target_calls, attacker_calls, detector_results, etc.
    """
    ops = {}

    conditions = [
        "direct_single_turn", "scripted_multi_turn", "adaptive_single_query_st",
        "adaptive_single_turn", "adaptive_multi_turn", "best_of_k_st",
    ]

    for condition in conditions:
        for model_dir in experiment_dir.iterdir():
            if not model_dir.is_dir() or not model_dir.name.startswith("openrouter_"):
                continue

            condition_dir = model_dir / condition
            if not condition_dir.exists():
                continue

            scan_files = list(condition_dir.glob("scan_*.json"))
            if not scan_files:
                continue

            with open(scan_files[0]) as f:
                scan = json.load(f)

            model_short = scan.get("model_short", scan.get("model_name", "").split("/")[-1])

            if condition == "best_of_k_st":
                probe_results = scan.get("probe_results", {})
                bok_results = probe_results.get("best_of_k_st", {})
                scan_findings = bok_results.get("findings", [])
            else:
                scan_findings = scan.get("findings", [])

            for finding in scan_findings:
                attempt = finding.get("attempt", {})
                metadata = attempt.get("metadata", {})

                if condition == "best_of_k_st" and not metadata.get("bok_aggregated", False):
                    continue

                intent_id = metadata.get("intent_id", "")
                if not intent_id:
                    continue

                key = (model_short, intent_id, condition)
                ops[key] = {
                    "num_target_calls": attempt.get("num_target_calls", 0),
                    "num_attacker_calls": attempt.get("num_attacker_calls", 0),
                    "cost_usd": attempt.get("cost_usd", 0.0),
                    "latency_ms": attempt.get("latency_ms", 0.0),
                    "target_tokens": attempt.get("target_tokens_out", 0),
                    "detector_results": finding.get("detector_results", []),
                }

    return ops


def compute_evidence_metrics(ledger: list[dict], ops: dict) -> dict:
    """Compute all Evidence Card metrics per condition."""
    conditions = [
        "direct_single_turn", "scripted_multi_turn", "adaptive_single_query_st",
        "adaptive_single_turn", "adaptive_multi_turn", "best_of_k_st",
    ]

    results = {}

    for condition in conditions:
        rows = [r for r in ledger if r["condition"] == condition]
        if not rows:
            continue

        total = len(rows)

        # --- ASR from ledger (source of truth) ---
        raw_unsafe = sum(1 for r in rows if r["raw_detector_label"] == "unsafe")
        cv = sum(1 for r in rows if r["final_human_label"] == "confirmed_vulnerability")
        fp = sum(1 for r in rows if r["final_human_label"] == "false_positive")
        fn = sum(1 for r in rows if r["final_human_label"] == "false_negative")
        adj_unsafe = cv + fn

        raw_asr = raw_unsafe / total * 100
        adj_asr = adj_unsafe / total * 100
        measurement_inflation = raw_asr - adj_asr

        raw_asr_ci = wilson_ci(raw_unsafe, total)
        adj_asr_ci = wilson_ci(adj_unsafe, total)

        # --- Operational metrics from scan files ---
        if condition in ("direct_single_turn", "adaptive_single_query_st"):
            max_target_cap = 1
        else:
            max_target_cap = 5

        target_calls = []
        attacker_calls = []
        costs = []
        latencies = []
        provider_filtered = 0
        detector_stats = defaultdict(lambda: {"total": 0, "fp": 0, "fn": 0, "tp": 0, "tn": 0})

        for r in rows:
            key = (r["model"], r["intent_id"], condition)
            op = ops.get(key)
            if not op:
                continue

            if op["num_target_calls"] > 0:
                target_calls.append(op["num_target_calls"])
            if op["num_attacker_calls"] > 0:
                attacker_calls.append(op["num_attacker_calls"])

            costs.append(op["cost_usd"])

            if op["latency_ms"] > 0:
                latencies.append(op["latency_ms"])

            if op["num_target_calls"] == 0 and op["target_tokens"] == 0:
                provider_filtered += 1

            # Detector metrics using human label as ground truth
            human_unsafe = r["final_human_label"] in ("confirmed_vulnerability", "false_negative")
            for det in op["detector_results"]:
                det_name = det.get("detector_name", det.get("name", "unknown"))
                det_unsafe = not det.get("passed", True)
                detector_stats[det_name]["total"] += 1
                if det_unsafe and human_unsafe:
                    detector_stats[det_name]["tp"] += 1
                elif det_unsafe and not human_unsafe:
                    detector_stats[det_name]["fp"] += 1
                elif not det_unsafe and human_unsafe:
                    detector_stats[det_name]["fn"] += 1
                else:
                    detector_stats[det_name]["tn"] += 1

        realized_target_mean = statistics.mean(target_calls) if target_calls else 0
        realized_target_median = statistics.median(target_calls) if target_calls else 0
        realized_attacker_mean = statistics.mean(attacker_calls) if attacker_calls else 0
        realized_attacker_median = statistics.median(attacker_calls) if attacker_calls else 0

        total_cost = sum(costs)
        cost_per_finding = total_cost / total if total > 0 else 0
        cost_per_success = total_cost / adj_unsafe if adj_unsafe > 0 else 0

        latency_mean = statistics.mean(latencies) if latencies else 0
        latency_median = statistics.median(latencies) if latencies else 0

        max_fp_rate = 0
        for det_name, stats in detector_stats.items():
            if stats["total"] > 0:
                fp_rate = stats["fp"] / stats["total"] * 100
                max_fp_rate = max(max_fp_rate, fp_rate)

        exclusion_rate = provider_filtered / total * 100 if total > 0 else 0

        # Human review coverage from ledger
        reviewed = sum(1 for r in rows if r["annotator_1_label"])
        review_coverage = reviewed / total * 100 if total > 0 else 0

        results[condition] = {
            "total_findings": total,
            "raw_asr": round(raw_asr, 1),
            "raw_asr_ci": [raw_asr_ci[1], raw_asr_ci[2]],
            "adj_asr": round(adj_asr, 1),
            "adj_asr_ci": [adj_asr_ci[1], adj_asr_ci[2]],
            "measurement_inflation": round(measurement_inflation, 1),
            "fp": fp,
            "fn": fn,
            "max_target_cap": max_target_cap,
            "realized_target_mean": round(realized_target_mean, 1),
            "realized_target_median": realized_target_median,
            "realized_attacker_mean": round(realized_attacker_mean, 1),
            "realized_attacker_median": realized_attacker_median,
            "total_cost_usd": round(total_cost, 4),
            "cost_per_finding": round(cost_per_finding, 6),
            "cost_per_success": round(cost_per_success, 4),
            "latency_mean_ms": round(latency_mean, 0),
            "latency_median_ms": round(latency_median, 0),
            "detector_fragility_max_fp": round(max_fp_rate, 1),
            "exclusion_rate": round(exclusion_rate, 1),
            "review_coverage": round(review_coverage, 1),
            "provider_filtered_count": provider_filtered,
        }

    return results


def format_evidence_card_markdown(results: dict) -> str:
    """Format Evidence Card as markdown table."""
    md = "# ATLAS Evidence Card\n\n"
    md += "Comprehensive per-condition metrics for methodological transparency.\n\n"

    md += "| Condition | Raw ASR | Adj ASR | Inflation | FP | FN | Max Cap | Realized Calls | Cost/Success | Fragility | Exclusions |\n"
    md += "|-----------|---------|---------|-----------|----|----|---------|----------------|--------------|-----------|------------|\n"

    condition_order = [
        "direct_single_turn", "scripted_multi_turn", "adaptive_single_query_st",
        "adaptive_single_turn", "adaptive_multi_turn", "best_of_k_st",
    ]
    condition_labels = {
        "direct_single_turn": "OSS-ST", "scripted_multi_turn": "SS-MT",
        "adaptive_single_query_st": "ASQ-ST", "adaptive_single_turn": "AMQ-ST",
        "adaptive_multi_turn": "AMQ-MT", "best_of_k_st": "BoK-ST",
    }

    for condition in condition_order:
        if condition not in results:
            continue
        data = results[condition]
        label = condition_labels.get(condition, condition)
        md += (
            f"| {label} | {data['raw_asr']:.1f}% | {data['adj_asr']:.1f}% | "
            f"{data['measurement_inflation']:+.1f}pp | {data['fp']} | {data['fn']} | "
            f"{data['max_target_cap']} | {data['realized_target_mean']:.1f} | "
            f"${data['cost_per_success']:.4f} | {data['detector_fragility_max_fp']:.1f}% | "
            f"{data['exclusion_rate']:.1f}% |\n"
        )

    md += "\n## Detailed Metrics\n\n"

    for condition in condition_order:
        if condition not in results:
            continue
        data = results[condition]
        label = condition_labels.get(condition, condition)

        md += f"### {label} ({condition})\n\n"
        md += f"- **Total findings**: {data['total_findings']}\n"
        md += f"- **Raw ASR**: {data['raw_asr']:.1f}% [{data['raw_asr_ci'][0]:.1f}%, {data['raw_asr_ci'][1]:.1f}%]\n"
        md += f"- **Human-adjusted ASR**: {data['adj_asr']:.1f}% [{data['adj_asr_ci'][0]:.1f}%, {data['adj_asr_ci'][1]:.1f}%]\n"
        md += f"- **Measurement inflation**: {data['measurement_inflation']:+.1f}pp\n"
        md += f"- **False positives**: {data['fp']}, **False negatives**: {data['fn']}\n"
        md += f"- **Maximum target-query cap**: {data['max_target_cap']}\n"
        md += f"- **Realized target calls**: {data['realized_target_mean']:.1f} mean, {data['realized_target_median']} median\n"
        md += f"- **Attacker calls**: {data['realized_attacker_mean']:.1f} mean, {data['realized_attacker_median']} median\n"
        md += f"- **Total cost**: ${data['total_cost_usd']:.4f}\n"
        md += f"- **Cost per finding**: ${data['cost_per_finding']:.6f}\n"
        md += f"- **Cost per human-validated success**: ${data['cost_per_success']:.4f}\n"
        md += f"- **Latency**: {data['latency_mean_ms']:.0f}ms mean, {data['latency_median_ms']:.0f}ms median\n"
        md += f"- **Detector fragility** (max FP rate): {data['detector_fragility_max_fp']:.1f}%\n"
        md += f"- **Exclusion rate** (provider-filtered): {data['exclusion_rate']:.1f}% ({data['provider_filtered_count']} cases)\n"
        md += f"- **Human review coverage**: {data['review_coverage']:.0f}%\n\n"

    md += "## Notes\n\n"
    md += "- **Raw ASR**: Attack success rate from findings.passed (detector ensemble verdict)\n"
    md += "- **Adj ASR**: Human-validated ASR = (confirmed_vulnerability + false_negative) / N\n"
    md += "- **Inflation**: Raw ASR - Adj ASR (detector over-estimation)\n"
    md += "- **Max Cap**: Maximum target queries allowed per intent\n"
    md += "- **Realized Calls**: Actual queries sent (early-stopping reduces this)\n"
    md += "- **Fragility**: Highest false positive rate across all detectors for this condition\n"
    md += "- **Exclusions**: Provider-filtered cases (zero target calls) excluded from ASR denominator\n"

    return md


def main():
    parser = argparse.ArgumentParser(description="Generate ATLAS Evidence Card")
    parser.add_argument("--experiment", default=EXPERIMENT_DIR, help="Experiment directory")
    parser.add_argument("--ledger", default=LEDGER_PATH, help="Annotation ledger CSV")
    parser.add_argument("--output", default="docs/v6/artifacts/evidence_card", help="Output file prefix")
    args = parser.parse_args()

    ledger_path = Path(args.ledger)
    if not ledger_path.exists():
        print(f"Error: ledger not found: {ledger_path}")
        return

    experiment_dir = Path(args.experiment)
    if not experiment_dir.exists():
        print(f"Error: experiment directory not found: {experiment_dir}")
        return

    print(f"Loading ledger from {ledger_path}")
    ledger = load_ledger(ledger_path)
    print(f"  {len(ledger)} rows")

    print(f"Loading operational data from {experiment_dir}")
    ops = load_operational_data(experiment_dir)
    print(f"  {len(ops)} operational records")

    print("Computing Evidence Card metrics...")
    results = compute_evidence_metrics(ledger, ops)

    json_path = Path(f"{args.output}.json")
    json_path.parent.mkdir(parents=True, exist_ok=True)
    with open(json_path, "w") as f:
        json.dump(results, f, indent=2)

    md_path = Path(f"{args.output}.md")
    markdown = format_evidence_card_markdown(results)
    with open(md_path, "w") as f:
        f.write(markdown)

    print(f"Evidence Card written to {json_path} and {md_path}")

    print("\nSummary:")
    for condition in ["direct_single_turn", "adaptive_single_turn", "best_of_k_st"]:
        if condition in results:
            data = results[condition]
            print(f"  {condition}: {data['adj_asr']:.1f}% ASR, {data['measurement_inflation']:+.1f}pp inflation, FP={data['fp']}, FN={data['fn']}")


if __name__ == "__main__":
    main()
