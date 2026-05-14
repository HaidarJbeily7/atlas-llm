#!/usr/bin/env python3
"""BoK K=1/3/5 ablation analysis using existing variant data.

Analyzes how ASR changes with different values of K (number of variants per intent)
using the pre-computed variant-level pass/fail data from the best_of_k_st scans.

Shows:
- ASR at K=1, K=3, K=5 (any-of-K rule)
- Marginal gains from K=3→5
- Per-model breakdown
- Wilson confidence intervals

Usage:
    python3 scripts/bok_k_ablation.py
    python3 scripts/bok_k_ablation.py --experiment docs/experiment/20260505_003630
"""
from __future__ import annotations

import argparse
import json
import math
from collections import defaultdict
from pathlib import Path

EXPERIMENT_DIR = "docs/experiment/20260505_003630"


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

                # Extract per-variant pass/fail (passed=False means attack succeeded)
                variant_results = []
                for variant in all_variants:
                    variant_passed = variant.get("passed", True)
                    variant_results.append(not variant_passed)  # Convert to attack_succeeded

                findings_by_model[model_short].append({
                    "intent_id": intent_id,
                    "variant_results": variant_results[:5],  # Ensure max K=5
                })

    return dict(findings_by_model)


def compute_k_ablation(findings_by_model: dict) -> dict:
    """Compute ASR for K=1, 3, 5 across all models."""
    results = {
        "overall": {},
        "per_model": {},
    }

    # Per-model analysis
    for model, findings in findings_by_model.items():
        model_results = {}

        for k in [1, 3, 5]:
            successes = 0
            total = 0

            for finding in findings:
                variants = finding["variant_results"][:k]
                if not variants:
                    continue

                # Any-of-K: attack succeeds if ANY variant succeeds
                attack_succeeded = any(variants)
                if attack_succeeded:
                    successes += 1
                total += 1

            asr, ci_low, ci_high = wilson_ci(successes, total)
            model_results[f"k_{k}"] = {
                "total": total,
                "successes": successes,
                "asr": asr,
                "ci": [ci_low, ci_high],
            }

        # Compute marginal gains
        if "k_3" in model_results and "k_5" in model_results:
            gain_3_to_5 = model_results["k_5"]["asr"] - model_results["k_3"]["asr"]
            model_results["marginal_gain_3_to_5"] = round(gain_3_to_5, 1)

        results["per_model"][model] = model_results

    # Overall analysis (pooled across models)
    overall_results = {}
    for k in [1, 3, 5]:
        total_successes = 0
        total_count = 0

        for model, findings in findings_by_model.items():
            for finding in findings:
                variants = finding["variant_results"][:k]
                if not variants:
                    continue

                attack_succeeded = any(variants)
                if attack_succeeded:
                    total_successes += 1
                total_count += 1

        asr, ci_low, ci_high = wilson_ci(total_successes, total_count)
        overall_results[f"k_{k}"] = {
            "total": total_count,
            "successes": total_successes,
            "asr": asr,
            "ci": [ci_low, ci_high],
        }

    # Overall marginal gain
    if "k_3" in overall_results and "k_5" in overall_results:
        gain_3_to_5 = overall_results["k_5"]["asr"] - overall_results["k_3"]["asr"]
        overall_results["marginal_gain_3_to_5"] = round(gain_3_to_5, 1)

    results["overall"] = overall_results
    return results


def format_markdown_table(results: dict) -> str:
    """Format results as markdown table."""
    md = "# BoK K=1/3/5 Ablation Analysis\n\n"

    # Overall results
    md += "## Overall Results\n\n"
    md += "| K | Total | Successes | ASR | 95% CI | Marginal Gain |\n"
    md += "|---|-------|-----------|-----|--------|--------------|\n"

    overall = results["overall"]
    for k in [1, 3, 5]:
        key = f"k_{k}"
        if key in overall:
            data = overall[key]
            ci_str = f"[{data['ci'][0]:.1f}%, {data['ci'][1]:.1f}%]"

            # Marginal gain (only for K=5)
            if k == 5 and "marginal_gain_3_to_5" in overall:
                gain = f"+{overall['marginal_gain_3_to_5']:.1f}pp"
            else:
                gain = "—"

            md += f"| {k} | {data['total']} | {data['successes']} | {data['asr']:.1f}% | {ci_str} | {gain} |\n"

    # Per-model results
    md += "\n## Per-Model Results\n\n"
    md += "| Model | K=1 ASR | K=3 ASR | K=5 ASR | Marginal Gain (3→5) |\n"
    md += "|-------|---------|---------|---------|--------------------|\n"

    per_model = results["per_model"]
    for model in sorted(per_model.keys()):
        data = per_model[model]
        k1_asr = data.get("k_1", {}).get("asr", 0)
        k3_asr = data.get("k_3", {}).get("asr", 0)
        k5_asr = data.get("k_5", {}).get("asr", 0)
        gain = data.get("marginal_gain_3_to_5", 0)

        md += f"| {model} | {k1_asr:.1f}% | {k3_asr:.1f}% | {k5_asr:.1f}% | +{gain:.1f}pp |\n"

    md += "\n## Analysis\n\n"

    # Extract overall K=5 vs K=1 comparison
    k1_asr = overall.get("k_1", {}).get("asr", 0)
    k5_asr = overall.get("k_5", {}).get("asr", 0)
    total_gain = k5_asr - k1_asr

    md += f"- **K=1 to K=5 total gain**: +{total_gain:.1f} percentage points\n"
    md += f"- **K=3 to K=5 marginal gain**: +{overall.get('marginal_gain_3_to_5', 0):.1f}pp (diminishing returns)\n"
    md += f"- **Optimal K**: K=5 achieves the highest ASR ({k5_asr:.1f}%) but with diminishing returns after K=3\n"

    return md


def main():
    parser = argparse.ArgumentParser(description="BoK K ablation analysis")
    parser.add_argument("--experiment", default=EXPERIMENT_DIR, help="Experiment directory")
    parser.add_argument("--output", default="docs/v6/artifacts/bok_k_ablation", help="Output file prefix")
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

    print("Computing K ablation...")
    results = compute_k_ablation(findings_by_model)

    # Output JSON
    json_path = Path(f"{args.output}.json")
    json_path.parent.mkdir(parents=True, exist_ok=True)
    with open(json_path, "w") as f:
        json.dump(results, f, indent=2)

    # Output Markdown
    md_path = Path(f"{args.output}.md")
    markdown = format_markdown_table(results)
    with open(md_path, "w") as f:
        f.write(markdown)

    print(f"Results written to {json_path} and {md_path}")

    # Print summary
    overall = results["overall"]
    k1_asr = overall.get("k_1", {}).get("asr", 0)
    k3_asr = overall.get("k_3", {}).get("asr", 0)
    k5_asr = overall.get("k_5", {}).get("asr", 0)
    print(f"Overall ASR: K=1: {k1_asr:.1f}%, K=3: {k3_asr:.1f}%, K=5: {k5_asr:.1f}%")


if __name__ == "__main__":
    main()