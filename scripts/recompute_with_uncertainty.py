#!/usr/bin/env python3
"""Recompute experiment metrics with confidence intervals and paired tests.

Reads scan result JSONs from an experiment directory and computes:
- ASR with 95% Wilson score CIs
- Cost/tokens/latency with 95% bootstrap CIs
- McNemar's test for paired ASR comparisons between conditions
- Wilcoxon signed-rank test for paired continuous metric comparisons

Usage:
    python scripts/recompute_with_uncertainty.py results/experiment/20260505_003630
    python scripts/recompute_with_uncertainty.py results/experiment/20260505_003630 \
        --verdicts annotation_platform/backend/r1_verdicts.json
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
from scipy import stats

# ---------------------------------------------------------------------------
# Wilson score CI for proportions
# ---------------------------------------------------------------------------


def wilson_ci(successes: int, n: int, z: float = 1.96) -> tuple[float, float, float]:
    """Wilson score interval for a binomial proportion.

    Returns (point_estimate, lower, upper).
    """
    if n == 0:
        return (0.0, 0.0, 0.0)
    p_hat = successes / n
    denom = 1 + z**2 / n
    centre = (p_hat + z**2 / (2 * n)) / denom
    margin = z / denom * math.sqrt(p_hat * (1 - p_hat) / n + z**2 / (4 * n**2))
    return (p_hat, max(0.0, centre - margin), min(1.0, centre + margin))


# ---------------------------------------------------------------------------
# Bootstrap CI for continuous metrics
# ---------------------------------------------------------------------------


def bootstrap_ci(
    values: list[float],
    n_boot: int = 10_000,
    ci: float = 0.95,
    statistic: str = "mean",
    rng_seed: int = 42,
) -> tuple[float, float, float]:
    """Bootstrap percentile CI.

    Returns (point_estimate, lower, upper).
    """
    if not values:
        return (0.0, 0.0, 0.0)
    arr = np.array(values)
    stat_fn = np.mean if statistic == "mean" else np.median
    point = float(stat_fn(arr))
    rng = np.random.default_rng(rng_seed)
    boot_stats = np.empty(n_boot)
    for i in range(n_boot):
        sample = rng.choice(arr, size=len(arr), replace=True)
        boot_stats[i] = stat_fn(sample)
    alpha = (1 - ci) / 2
    lower = float(np.percentile(boot_stats, 100 * alpha))
    upper = float(np.percentile(boot_stats, 100 * (1 - alpha)))
    return (point, lower, upper)


# ---------------------------------------------------------------------------
# McNemar's exact test
# ---------------------------------------------------------------------------


def mcnemar_test(
    outcomes_a: list[bool], outcomes_b: list[bool]
) -> dict:
    """McNemar's exact test on paired binary outcomes.

    Returns dict with statistic, p_value, n_discordant, and the 2x2 table.
    """
    assert len(outcomes_a) == len(outcomes_b)
    # b = A fails, B succeeds; c = A succeeds, B fails
    b = sum(1 for a, bv in zip(outcomes_a, outcomes_b) if not a and bv)
    c = sum(1 for a, bv in zip(outcomes_a, outcomes_b) if a and not bv)
    n_discordant = b + c
    if n_discordant == 0:
        return {"statistic": 0.0, "p_value": 1.0, "b": b, "c": c, "n_discordant": 0}
    # Exact binomial test (two-sided)
    p_value = float(stats.binomtest(b, n_discordant, 0.5).pvalue)
    return {"statistic": float(b), "p_value": p_value, "b": b, "c": c, "n_discordant": n_discordant}


# ---------------------------------------------------------------------------
# Extract records from scan JSONs
# ---------------------------------------------------------------------------


def extract_records(experiment_dir: Path) -> list[dict]:
    """Walk experiment directory and extract per-finding records."""
    records = []
    for scan_path in sorted(experiment_dir.rglob("scan_*.json")):
        with open(scan_path) as f:
            scan = json.load(f)

        model = scan.get("model_name", "")
        # Derive condition from directory structure: .../model_slug/condition/scan_*.json
        condition = scan_path.parent.name

        for finding in scan.get("findings", []):
            attempt = finding.get("attempt", {})
            metadata = attempt.get("metadata", {})
            intent_id = metadata.get("intent_id", "")

            # Majority vote from detector results
            detector_results = finding.get("detector_results", [])
            n_fail = sum(1 for d in detector_results if not d.get("passed", True))
            n_total = len(detector_results)
            majority_fail = n_fail > n_total / 2 if n_total > 0 else False

            records.append({
                "model": model,
                "condition": condition,
                "intent_id": intent_id,
                "finding_id": finding.get("id", ""),
                "passed": finding.get("passed", True),
                "majority_fail": majority_fail,
                "cost_usd": attempt.get("cost_usd", 0.0) or 0.0,
                "target_tokens_in": attempt.get("target_tokens_in", 0) or 0,
                "target_tokens_out": attempt.get("target_tokens_out", 0) or 0,
                "attacker_tokens_in": attempt.get("attacker_tokens_in", 0) or 0,
                "attacker_tokens_out": attempt.get("attacker_tokens_out", 0) or 0,
                "latency_ms": attempt.get("latency_ms", 0.0) or 0.0,
                "num_target_calls": attempt.get("num_target_calls", 0) or 0,
                "num_attacker_calls": attempt.get("num_attacker_calls", 0) or 0,
                "pair_score": metadata.get("pair_score", None),
                "total_attacker_iterations": metadata.get("total_attacker_iterations", None),
            })

    return records


def load_human_verdicts(verdicts_path: Path) -> dict[str, str]:
    """Load human verdicts as finding_id -> verdict mapping.

    Handles both formats:
    - Unanimous: r1_verdict = CORRECT | FALSE_POSITIVE | FALSE_NEGATIVE
    - Split: vote_status = confirmed_safe | confirmed_vulnerability | false_positive | false_negative
    """
    with open(verdicts_path) as f:
        data = json.load(f)
    verdicts = data.get("verdicts", [])
    result = {}
    for v in verdicts:
        fid = v.get("finding_id")
        if not fid:
            continue
        if "r1_verdict" in v:
            result[fid] = v["r1_verdict"]
        elif "vote_status" in v:
            # Map split verdict format to the CORRECT/FALSE_POSITIVE/FALSE_NEGATIVE format
            status = v["vote_status"]
            if status in ("confirmed_safe", "confirmed_vulnerability"):
                result[fid] = "CORRECT"
            elif status == "false_positive":
                result[fid] = "FALSE_POSITIVE"
            elif status == "false_negative":
                result[fid] = "FALSE_NEGATIVE"
    return result


# ---------------------------------------------------------------------------
# Compute metrics per condition and per model x condition
# ---------------------------------------------------------------------------


def compute_asr(records: list[dict], human_verdicts: dict[str, str] | None = None) -> dict:
    """Compute ASR (attack success rate = fraction of findings that FAILED safety).

    A finding is an attack success if passed=False (i.e. the model was unsafe).
    If human verdicts are available, adjust: INCORRECT verdicts flip the outcome.
    """
    successes = 0
    for r in records:
        attack_succeeded = not r["passed"]
        if human_verdicts and r["finding_id"] in human_verdicts:
            verdict = human_verdicts[r["finding_id"]]
            if verdict == "INCORRECT":
                attack_succeeded = not attack_succeeded
        if attack_succeeded:
            successes += 1
    return {
        "n": len(records),
        "successes": successes,
        **dict(zip(["asr", "ci_lower", "ci_upper"], wilson_ci(successes, len(records)))),
    }


def compute_continuous_metrics(records: list[dict]) -> dict:
    """Compute bootstrap CIs for continuous metrics."""
    costs = [r["cost_usd"] for r in records]
    total_tokens = [
        r["target_tokens_in"] + r["target_tokens_out"]
        + r["attacker_tokens_in"] + r["attacker_tokens_out"]
        for r in records
    ]
    latencies = [r["latency_ms"] for r in records]
    target_calls = [float(r["num_target_calls"]) for r in records]
    attacker_calls = [float(r["num_attacker_calls"]) for r in records]

    result = {}
    for name, values, stat in [
        ("cost_usd", costs, "mean"),
        ("total_tokens", total_tokens, "mean"),
        ("latency_ms", latencies, "median"),
        ("target_calls", target_calls, "mean"),
        ("attacker_calls", attacker_calls, "mean"),
    ]:
        pt, lo, hi = bootstrap_ci(values, statistic=stat)
        result[name] = {"point": pt, "ci_lower": lo, "ci_upper": hi, "statistic": stat}
    return result


# ---------------------------------------------------------------------------
# Paired comparisons
# ---------------------------------------------------------------------------


def paired_asr_comparison(
    records_a: list[dict],
    records_b: list[dict],
    human_verdicts: dict[str, str] | None = None,
) -> dict:
    """McNemar's test comparing ASR between two conditions on matched intent-model pairs."""
    # Index by (model, intent_id)
    index_a = {(r["model"], r["intent_id"]): r for r in records_a}
    index_b = {(r["model"], r["intent_id"]): r for r in records_b}
    common_keys = sorted(set(index_a.keys()) & set(index_b.keys()))

    if not common_keys:
        return {"error": "no matched pairs", "n_pairs": 0}

    def attack_success(r: dict) -> bool:
        succeeded = not r["passed"]
        if human_verdicts and r["finding_id"] in human_verdicts:
            if human_verdicts[r["finding_id"]] == "INCORRECT":
                succeeded = not succeeded
        return succeeded

    outcomes_a = [attack_success(index_a[k]) for k in common_keys]
    outcomes_b = [attack_success(index_b[k]) for k in common_keys]

    result = mcnemar_test(outcomes_a, outcomes_b)
    result["n_pairs"] = len(common_keys)

    # Risk difference with CI
    asr_a = sum(outcomes_a) / len(outcomes_a)
    asr_b = sum(outcomes_b) / len(outcomes_b)
    result["asr_a"] = asr_a
    result["asr_b"] = asr_b
    result["risk_difference"] = asr_b - asr_a
    return result


def paired_continuous_comparison(
    records_a: list[dict],
    records_b: list[dict],
    metric: str,
) -> dict:
    """Wilcoxon signed-rank test for a continuous metric on matched pairs."""
    index_a = {(r["model"], r["intent_id"]): r for r in records_a}
    index_b = {(r["model"], r["intent_id"]): r for r in records_b}
    common_keys = sorted(set(index_a.keys()) & set(index_b.keys()))

    if not common_keys:
        return {"error": "no matched pairs", "n_pairs": 0}

    values_a = []
    values_b = []
    for k in common_keys:
        va = index_a[k].get(metric, 0.0) or 0.0
        vb = index_b[k].get(metric, 0.0) or 0.0
        values_a.append(va)
        values_b.append(vb)

    diffs = [b - a for a, b in zip(values_a, values_b)]
    # Filter zero diffs (Wilcoxon requires non-zero diffs)
    nonzero = [(a, b) for a, b in zip(values_a, values_b) if a != b]
    if not nonzero:
        return {
            "statistic": 0.0, "p_value": 1.0, "n_pairs": len(common_keys),
            "mean_a": float(np.mean(values_a)), "mean_b": float(np.mean(values_b)),
            "mean_diff": 0.0,
        }

    stat_result = stats.wilcoxon(values_a, values_b, alternative="two-sided")
    return {
        "statistic": float(stat_result.statistic),
        "p_value": float(stat_result.pvalue),
        "n_pairs": len(common_keys),
        "mean_a": float(np.mean(values_a)),
        "mean_b": float(np.mean(values_b)),
        "mean_diff": float(np.mean(diffs)),
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(description="Recompute metrics with uncertainty")
    parser.add_argument("experiment_dir", type=Path, help="Path to experiment results directory")
    parser.add_argument("--verdicts", type=Path, default=None, help="Path to human verdicts JSON")
    parser.add_argument(
        "--output-dir", type=Path, default=None,
        help="Output directory (default: results/analysis/)",
    )
    args = parser.parse_args()

    if not args.experiment_dir.is_dir():
        print(f"ERROR: {args.experiment_dir} is not a directory", file=sys.stderr)
        sys.exit(1)

    output_dir = args.output_dir or Path("results/analysis")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Load data
    print(f"Loading scan results from {args.experiment_dir} ...")
    records = extract_records(args.experiment_dir)
    print(f"  Found {len(records)} findings")

    human_verdicts = None
    if args.verdicts and args.verdicts.exists():
        human_verdicts = load_human_verdicts(args.verdicts)
        print(f"  Loaded {len(human_verdicts)} human verdicts")

    # Group by condition
    by_condition: dict[str, list[dict]] = defaultdict(list)
    for r in records:
        by_condition[r["condition"]].append(r)

    conditions = sorted(by_condition.keys())
    print(f"  Conditions: {conditions}")

    # Group by (model, condition)
    by_model_condition: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for r in records:
        by_model_condition[(r["model"], r["condition"])].append(r)

    models = sorted({r["model"] for r in records})

    # -----------------------------------------------------------------------
    # 1. Per-condition metrics
    # -----------------------------------------------------------------------
    print("\nComputing per-condition metrics ...")
    condition_metrics = {}
    for cond in conditions:
        recs = by_condition[cond]
        asr_data = compute_asr(recs, human_verdicts)
        cont_data = compute_continuous_metrics(recs)
        condition_metrics[cond] = {"asr": asr_data, **cont_data}

    # -----------------------------------------------------------------------
    # 2. Per model x condition metrics
    # -----------------------------------------------------------------------
    print("Computing per model x condition metrics ...")
    cell_metrics = {}
    for model in models:
        cell_metrics[model] = {}
        for cond in conditions:
            key = (model, cond)
            if key in by_model_condition:
                recs = by_model_condition[key]
                asr_data = compute_asr(recs, human_verdicts)
                cont_data = compute_continuous_metrics(recs)
                cell_metrics[model][cond] = {"asr": asr_data, **cont_data}

    # -----------------------------------------------------------------------
    # 3. Paired comparisons
    # -----------------------------------------------------------------------
    print("Running paired comparisons ...")
    paired_tests = {}
    condition_pairs = []
    for i, c1 in enumerate(conditions):
        for c2 in conditions[i + 1:]:
            condition_pairs.append((c1, c2))

    for c1, c2 in condition_pairs:
        pair_key = f"{c1}_vs_{c2}"

        # Pooled across models
        asr_test = paired_asr_comparison(by_condition[c1], by_condition[c2], human_verdicts)
        cost_test = paired_continuous_comparison(by_condition[c1], by_condition[c2], "cost_usd")
        latency_test = paired_continuous_comparison(
            by_condition[c1], by_condition[c2], "latency_ms"
        )

        paired_tests[pair_key] = {
            "pooled": {
                "asr_mcnemar": asr_test,
                "cost_wilcoxon": cost_test,
                "latency_wilcoxon": latency_test,
            },
        }

        # Per-model breakdowns
        per_model = {}
        for model in models:
            k1, k2 = (model, c1), (model, c2)
            if k1 in by_model_condition and k2 in by_model_condition:
                per_model[model] = {
                    "asr_mcnemar": paired_asr_comparison(
                        by_model_condition[k1], by_model_condition[k2], human_verdicts,
                    ),
                }
        paired_tests[pair_key]["per_model"] = per_model

    # Apply Bonferroni correction to pooled tests
    n_comparisons = len(condition_pairs)
    for pair_key in paired_tests:
        pooled = paired_tests[pair_key]["pooled"]
        for test_key in ["asr_mcnemar", "cost_wilcoxon", "latency_wilcoxon"]:
            if "p_value" in pooled[test_key]:
                raw_p = pooled[test_key]["p_value"]
                pooled[test_key]["p_value_bonferroni"] = min(1.0, raw_p * n_comparisons)
                pooled[test_key]["n_comparisons_bonferroni"] = n_comparisons

    # -----------------------------------------------------------------------
    # 4. Pairing audit — prove (model, intent_id) alignment
    # -----------------------------------------------------------------------
    print("Building pairing audit ...")

    # Collect intent_ids per (model, condition)
    intent_sets: dict[tuple[str, str], list[str]] = defaultdict(list)
    for r in records:
        intent_sets[(r["model"], r["condition"])].append(r["intent_id"])

    # Build per-model audit: verify all conditions share same intent_ids in same order
    per_model_audit = []
    all_aligned = True
    for model in models:
        model_short = model.split("/")[-1] if "/" in model else model
        model_entry: dict = {"model": model_short, "conditions": {}}
        ref_intents: list[str] | None = None
        for cond in conditions:
            intents = intent_sets.get((model, cond), [])
            model_entry["conditions"][cond] = {
                "n_intents": len(intents),
                "n_unique": len(set(intents)),
                "first_3": intents[:3],
                "last_3": intents[-3:] if len(intents) >= 3 else intents,
            }
            if ref_intents is None:
                ref_intents = intents
            elif intents != ref_intents:
                all_aligned = False
                model_entry["aligned"] = False
        if "aligned" not in model_entry:
            model_entry["aligned"] = True
        per_model_audit.append(model_entry)

    # Build per-comparison audit: show matched pair counts
    per_comparison_audit = []
    for c1, c2 in condition_pairs:
        pair_key = f"{c1}_vs_{c2}"
        index_a = {(r["model"], r["intent_id"]): r for r in by_condition[c1]}
        index_b = {(r["model"], r["intent_id"]): r for r in by_condition[c2]}
        common = sorted(set(index_a.keys()) & set(index_b.keys()))
        only_a = set(index_a.keys()) - set(index_b.keys())
        only_b = set(index_b.keys()) - set(index_a.keys())
        per_comparison_audit.append({
            "comparison": pair_key,
            "matched_pairs": len(common),
            "unmatched_a_only": len(only_a),
            "unmatched_b_only": len(only_b),
            "join_key": "(model, intent_id)",
        })

    # Unique intent list
    unique_intents = sorted(set(r["intent_id"] for r in records))

    pairing_audit = {
        "join_key": "(model, intent_id)",
        "total_records": len(records),
        "n_models": len(models),
        "n_conditions": len(conditions),
        "n_unique_intents": len(unique_intents),
        "intent_list": unique_intents,
        "all_models_aligned": all_aligned,
        "per_model": per_model_audit,
        "per_comparison": per_comparison_audit,
    }

    # -----------------------------------------------------------------------
    # 5. Write outputs
    # -----------------------------------------------------------------------
    print(f"\nWriting outputs to {output_dir} ...")

    # Machine-readable
    full_results = {
        "experiment_dir": str(args.experiment_dir),
        "n_findings": len(records),
        "models": models,
        "conditions": conditions,
        "condition_metrics": condition_metrics,
        "cell_metrics": cell_metrics,
        "paired_tests": paired_tests,
        "pairing_audit": pairing_audit,
    }
    metrics_json_path = output_dir / "metrics_with_ci.json"
    with open(metrics_json_path, "w") as f:
        json.dump(full_results, f, indent=2, default=str)
    print(f"  {metrics_json_path}")

    paired_json_path = output_dir / "paired_tests.json"
    with open(paired_json_path, "w") as f:
        json.dump(paired_tests, f, indent=2, default=str)
    print(f"  {paired_json_path}")

    audit_json_path = output_dir / "pairing_audit.json"
    with open(audit_json_path, "w") as f:
        json.dump(pairing_audit, f, indent=2, default=str)
    print(f"  {audit_json_path}")

    # Markdown tables
    md_path = output_dir / "metrics_with_ci.md"
    with open(md_path, "w") as f:
        f.write("# Experiment Metrics with Confidence Intervals\n\n")
        f.write(f"Source: `{args.experiment_dir}`\n\n")

        # Condition-level ASR table
        f.write("## ASR by Condition (pooled across models)\n\n")
        f.write("| Condition | N | Successes | ASR | 95% CI |\n")
        f.write("| --- | --- | --- | --- | --- |\n")
        for cond in conditions:
            m = condition_metrics[cond]["asr"]
            f.write(
                f"| `{cond}` | {m['n']} | {m['successes']} "
                f"| {m['asr']:.1%} | [{m['ci_lower']:.1%}, {m['ci_upper']:.1%}] |\n"
            )

        # Condition-level cost/latency table
        f.write("\n## Cost & Latency by Condition\n\n")
        f.write("| Condition | Cost/attack (mean) | 95% CI | Latency/attack (median) | 95% CI |\n")
        f.write("| --- | --- | --- | --- | --- |\n")
        for cond in conditions:
            cm = condition_metrics[cond]
            cost = cm["cost_usd"]
            lat = cm["latency_ms"]
            f.write(
                f"| `{cond}` "
                f"| ${cost['point']:.4f} | [${cost['ci_lower']:.4f}, ${cost['ci_upper']:.4f}] "
                f"| {lat['point']:.0f}ms | [{lat['ci_lower']:.0f}ms, {lat['ci_upper']:.0f}ms] |\n"
            )

        # Per-model ASR table
        f.write("\n## ASR by Model x Condition\n\n")
        f.write("| Model | " + " | ".join(f"`{c}`" for c in conditions) + " |\n")
        f.write("| --- |" + " --- |" * len(conditions) + "\n")
        for model in models:
            short_model = model.split("/")[-1] if "/" in model else model
            row = f"| {short_model} |"
            for cond in conditions:
                if cond in cell_metrics.get(model, {}):
                    m = cell_metrics[model][cond]["asr"]
                    row += f" {m['asr']:.0%} [{m['ci_lower']:.0%}-{m['ci_upper']:.0%}] |"
                else:
                    row += " — |"
            f.write(row + "\n")

        # Paired test results (key comparisons)
        f.write("\n## Paired Comparisons (McNemar, pooled)\n\n")
        f.write(
            "| Comparison | ASR_A | ASR_B | Risk Diff | p-value | "
            "p (Bonferroni) | Discordant |\n"
        )
        f.write("| --- | --- | --- | --- | --- | --- | --- |\n")
        for c1, c2 in condition_pairs:
            pair_key = f"{c1}_vs_{c2}"
            t = paired_tests[pair_key]["pooled"]["asr_mcnemar"]
            if "error" in t:
                f.write(f"| `{c1}` vs `{c2}` | — | — | — | — | — | — |\n")
                continue
            sig = "**" if t.get("p_value_bonferroni", 1.0) < 0.05 else ""
            f.write(
                f"| `{c1}` vs `{c2}` "
                f"| {t['asr_a']:.1%} | {t['asr_b']:.1%} "
                f"| {t['risk_difference']:+.1%} "
                f"| {t['p_value']:.4f} "
                f"| {sig}{t.get('p_value_bonferroni', t['p_value']):.4f}{sig} "
                f"| {t['n_discordant']} |\n"
            )

    print(f"  {md_path}")
    print("\nDone.")


if __name__ == "__main__":
    main()
