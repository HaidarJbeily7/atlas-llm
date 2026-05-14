#!/usr/bin/env python3
"""BoK sequential (early-stopping) simulation using existing variant data.

Simulates sequential execution: try variant 0, if it succeeds stop; otherwise
try variant 1, etc. Shows how many variants are actually needed on average
and compares to always sending all K=5 variants.

This directly supports the "maximum target-query cap vs. realized target calls"
distinction from Fix 3.

Usage:
    python3 scripts/bok_sequential_stopping.py
    python3 scripts/bok_sequential_stopping.py --experiment docs/experiment/20260505_003630
"""
from __future__ import annotations

import argparse
import json
import statistics
from collections import Counter, defaultdict
from pathlib import Path

EXPERIMENT_DIR = "docs/experiment/20260505_003630"


def load_bok_findings(experiment_dir: Path) -> dict:
    """Load BoK findings from all model scans."""
    findings_by_model = defaultdict(list)

    # Find all best_of_k_st scan files
    for model_dir in experiment_dir.iterdir():
        if not model_dir.is_dir():
            continue

        bok_dir = model_dir / "best_of_k_st"
        if not bok_dir.exists():
            continue

        for scan_file in bok_dir.glob("scan_*.json"):
            with open(scan_file) as f:
                scan = json.load(f)

            model_short = scan.get("model_short", scan.get("model_name", "").split("/")[-1])

            # Extract findings from probe_results.best_of_k_st.findings
            probe_results = scan.get("probe_results", {})
            bok_results = probe_results.get("best_of_k_st", {})
            for finding in bok_results.get("findings", []):
                # Extract variant-level data from bok_all_variants
                attempt = finding.get("attempt", {})
                metadata = attempt.get("metadata", {})

                # Only process aggregated BoK findings (not raw variants)
                if not metadata.get("bok_aggregated", False):
                    continue

                all_variants = metadata.get("bok_all_variants", [])
                if not all_variants:
                    continue

                intent_id = metadata.get("intent_id", "")

                # Extract per-variant pass/fail
                variant_results = []

                for variant in all_variants:
                    variant_passed = variant.get("passed", True)
                    attack_succeeded = not variant_passed

                    variant_results.append({
                        "attack_succeeded": attack_succeeded,
                    })

                # Total cost/latency for this finding (all K=5 variants combined)
                total_cost = finding.get("cost_usd", 0.0)
                total_latency = finding.get("latency_ms", 0.0)

                findings_by_model[model_short].append({
                    "intent_id": intent_id,
                    "variant_results": variant_results[:5],  # Ensure max K=5
                    "total_cost_k5": total_cost,
                    "total_latency_k5": total_latency,
                })

    return dict(findings_by_model)


def simulate_sequential_stopping(findings_by_model: dict) -> dict:
    """Simulate sequential execution with early stopping."""
    results = {
        "overall": {},
        "per_model": {},
        "distribution": {},
    }

    # Per-model simulation
    for model, findings in findings_by_model.items():
        stopping_points = []  # Which variant index caused success (0-4) or "never"
        realized_queries = []  # Number of queries actually sent (1-5)

        for finding in findings:
            variants = finding["variant_results"]

            # Simulate sequential execution
            found_success = False

            for i, variant in enumerate(variants):
                if variant["attack_succeeded"]:
                    # Success! Stop here
                    stopping_points.append(i)
                    realized_queries.append(i + 1)
                    found_success = True
                    break

            if not found_success:
                # All variants failed
                stopping_points.append("never")
                realized_queries.append(len(variants))

        # Compute statistics for this model
        mean_realized = statistics.mean(realized_queries)
        median_realized = statistics.median(realized_queries)
        stopping_dist = Counter(stopping_points)

        # Compute theoretical cost savings: sequential uses fewer queries
        # (actual cost data not available per variant)
        theoretical_savings = (5.0 - mean_realized) / 5.0 * 100

        results["per_model"][model] = {
            "total_intents": len(findings),
            "mean_realized_queries": round(mean_realized, 2),
            "median_realized_queries": median_realized,
            "stopping_distribution": dict(stopping_dist),
            "theoretical_savings_pct": round(theoretical_savings, 1),
        }

    # Overall (pooled) analysis
    all_realized_queries = []
    all_stopping_points = []

    for model_data in results["per_model"].values():
        # Add stopping point counts to get individual data points
        for stop_point, count in model_data["stopping_distribution"].items():
            all_stopping_points.extend([stop_point] * count)

        # Reconstruct realized queries from stopping points
        for stop_point, count in model_data["stopping_distribution"].items():
            if stop_point == "never":
                all_realized_queries.extend([5] * count)
            else:
                all_realized_queries.extend([int(stop_point) + 1] * count)

    overall_mean_realized = statistics.mean(all_realized_queries)
    overall_median_realized = statistics.median(all_realized_queries)
    overall_stopping_dist = Counter(all_stopping_points)

    overall_theoretical_savings = (5.0 - overall_mean_realized) / 5.0 * 100

    results["overall"] = {
        "total_intents": len(all_realized_queries),
        "mean_realized_queries": round(overall_mean_realized, 2),
        "median_realized_queries": overall_median_realized,
        "stopping_distribution": dict(overall_stopping_dist),
        "theoretical_savings_pct": round(overall_theoretical_savings, 1),
    }

    # Stopping distribution as percentages
    total_stops = sum(overall_stopping_dist.values())
    results["distribution"] = {
        str(k): round(v / total_stops * 100, 1)
        for k, v in overall_stopping_dist.items()
    }

    return results


def format_markdown(results: dict) -> str:
    """Format results as markdown."""
    md = "# BoK Sequential Stopping Simulation\n\n"

    md += "## Overall Results\n\n"
    overall = results["overall"]

    md += "### Query Efficiency\n\n"
    md += f"- **Mean realized queries**: {overall['mean_realized_queries']}/5.0 ({overall['mean_realized_queries']/5*100:.1f}% of max cap)\n"
    md += f"- **Median realized queries**: {overall['median_realized_queries']}/5\n"
    md += f"- **Theoretical query savings**: {overall['theoretical_savings_pct']:.1f}% (proportional cost savings)\n\n"

    md += "### Stopping Distribution\n\n"
    dist = results["distribution"]
    md += "| Stop Point | Percentage |\n"
    md += "|------------|-----------|\n"
    for k in ["0", "1", "2", "3", "4", "never"]:
        if k in dist:
            label = f"Variant {int(k)+1}" if k.isdigit() else "Never (all failed)"
            md += f"| {label} | {dist[k]:.1f}% |\n"

    md += "\n## Per-Model Results\n\n"
    md += "| Model | Mean Realized | Theoretical Savings | Stop at V1 | Stop at V2 | Stop at V3 | Never |\n"
    md += "|-------|---------------|---------------------|-------------|-------------|-------------|-------|\n"

    per_model = results["per_model"]
    for model in sorted(per_model.keys()):
        data = per_model[model]
        dist = data["stopping_distribution"]
        total = data["total_intents"]

        v1_pct = dist.get("0", 0) / total * 100
        v2_pct = dist.get("1", 0) / total * 100
        v3_pct = dist.get("2", 0) / total * 100
        never_pct = dist.get("never", 0) / total * 100

        md += f"| {model} | {data['mean_realized_queries']:.1f}/5.0 | {data['theoretical_savings_pct']:.1f}% | {v1_pct:.1f}% | {v2_pct:.1f}% | {v3_pct:.1f}% | {never_pct:.1f}% |\n"

    md += "\n## Analysis\n\n"
    md += f"Sequential BoK execution realizes {overall['mean_realized_queries']:.1f} target queries on average vs. the maximum cap of 5, providing {overall['theoretical_savings_pct']:.1f}% theoretical savings. "

    # Find most common stopping point
    dist = results["distribution"]
    max_stop = max(dist.items(), key=lambda x: x[1])
    if max_stop[0].isdigit():
        stop_desc = f"Variant {int(max_stop[0])+1}"
    else:
        stop_desc = "never"

    md += f"Most attacks succeed at {stop_desc} ({max_stop[1]:.1f}%), showing that early variants capture most of the attack surface.\n\n"

    md += "This supports the distinction between **maximum target-query cap** (matched between BoK-ST and PAIR-5 at K=5) and **realized target calls** "
    md += f"(sequential BoK: {overall['mean_realized_queries']:.1f}, while PAIR-5 early-stops are not analyzed here but likely similar)."

    return md


def main():
    parser = argparse.ArgumentParser(description="BoK sequential stopping simulation")
    parser.add_argument("--experiment", default=EXPERIMENT_DIR, help="Experiment directory")
    parser.add_argument("--output", default="docs/v6/artifacts/bok_sequential_stopping", help="Output file prefix")
    args = parser.parse_args()

    experiment_dir = Path(args.experiment)
    if not experiment_dir.exists():
        print(f"Error: experiment directory not found: {experiment_dir}")
        return

    print(f"Loading BoK findings from {experiment_dir}")
    findings_by_model = load_bok_findings(experiment_dir)

    if not findings_by_model:
        print("Error: No BoK findings found")
        return

    print(f"Found BoK data for {len(findings_by_model)} models")
    for model, findings in findings_by_model.items():
        print(f"  {model}: {len(findings)} intents")

    print("Simulating sequential stopping...")
    results = simulate_sequential_stopping(findings_by_model)

    # Output JSON
    json_path = Path(f"{args.output}.json")
    json_path.parent.mkdir(parents=True, exist_ok=True)
    with open(json_path, "w") as f:
        json.dump(results, f, indent=2)

    # Output Markdown
    md_path = Path(f"{args.output}.md")
    markdown = format_markdown(results)
    with open(md_path, "w") as f:
        f.write(markdown)

    print(f"Results written to {json_path} and {md_path}")

    # Print summary
    overall = results["overall"]
    print(f"Mean realized queries: {overall['mean_realized_queries']:.1f}/5.0")
    print(f"Theoretical savings: {overall['theoretical_savings_pct']:.1f}%")
    print(f"Most common stop: {max(results['distribution'].items(), key=lambda x: x[1])}")


if __name__ == "__main__":
    main()