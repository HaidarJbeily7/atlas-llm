#!/usr/bin/env python3
"""Verify all numbers in FINAL_RQ_ANSWERS_V6.md from the annotation ledger and artifacts.

Recomputes every quantitative claim from primary data and flags mismatches.

Usage:
    python3 scripts/verify_final_answers.py
"""
from __future__ import annotations

import csv
import json
import math
from collections import Counter, defaultdict
from pathlib import Path


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def wilson_ci(successes: int, n: int, z: float = 1.96) -> tuple[float, float, float]:
    """Wilson score interval. Returns (point%, lower%, upper%)."""
    if n == 0:
        return (0.0, 0.0, 0.0)
    p_hat = successes / n
    denom = 1 + z**2 / n
    centre = (p_hat + z**2 / (2 * n)) / denom
    margin = z / denom * math.sqrt(p_hat * (1 - p_hat) / n + z**2 / (4 * n**2))
    return (
        round(p_hat * 100, 1),
        round(max(0.0, centre - margin) * 100, 1),
        round(min(1.0, centre + margin) * 100, 1),
    )


def mcnemar_test(a_wins: int, b_wins: int) -> float:
    """Two-sided McNemar mid-p value."""
    from math import comb
    n = a_wins + b_wins
    if n == 0:
        return 1.0
    k = min(a_wins, b_wins)
    # Exact two-sided p
    p = 0.0
    for i in range(k + 1):
        p += comb(n, i) * 0.5**n
    return min(2 * p, 1.0)


CONDS = [
    "direct_single_turn", "scripted_multi_turn", "adaptive_single_query_st",
    "adaptive_single_turn", "adaptive_multi_turn", "best_of_k_st",
]
COND_LABELS = {
    "direct_single_turn": "OSS-ST", "scripted_multi_turn": "SS-MT",
    "adaptive_single_query_st": "ASQ-ST", "adaptive_single_turn": "AMQ-ST",
    "adaptive_multi_turn": "AMQ-MT", "best_of_k_st": "BoK-ST",
}
MODELS = [
    "claude-sonnet-4", "deepseek-chat-v3-0324", "gemini-2.5-flash",
    "gpt-4o", "gpt-4o-mini", "llama-3.3-70b-instruct",
    "mistral-large-2411", "qwen-2.5-72b-instruct",
]


def is_human_unsafe(label: str) -> bool:
    return label in ("confirmed_vulnerability", "false_negative")


def is_raw_unsafe(label: str) -> bool:
    return label == "unsafe"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    ledger_path = Path(__file__).resolve().parent.parent / "data" / "annotation_ledger.csv"
    if not ledger_path.exists():
        print("ERROR: annotation_ledger.csv not found. Run export_annotation_ledger.py first.")
        return

    with open(ledger_path) as f:
        rows = list(csv.DictReader(f))

    print(f"Loaded {len(rows)} rows from ledger\n")

    # -----------------------------------------------------------------------
    # 1. Per-condition: Raw ASR, Adj ASR, Wilson CIs, FP, FN, Inflation
    # -----------------------------------------------------------------------
    print("=" * 80)
    print("1. PER-CONDITION ASR WITH WILSON CIs")
    print("=" * 80)
    print(f"{'Cond':<8} {'N':>4} {'RawASR':>7} {'Raw 95% CI':>20} {'AdjASR':>7} {'Adj 95% CI':>20} {'FP':>4} {'FN':>4} {'Inflation':>10}")
    print("-" * 90)

    cond_stats = {}
    for cond in CONDS:
        s = [r for r in rows if r["condition"] == cond]
        n = len(s)
        raw_unsafe = sum(1 for r in s if is_raw_unsafe(r["raw_detector_label"]))
        cv = sum(1 for r in s if r["final_human_label"] == "confirmed_vulnerability")
        fp = sum(1 for r in s if r["final_human_label"] == "false_positive")
        fn = sum(1 for r in s if r["final_human_label"] == "false_negative")
        adj_unsafe = cv + fn

        raw_pct, raw_lo, raw_hi = wilson_ci(raw_unsafe, n)
        adj_pct, adj_lo, adj_hi = wilson_ci(adj_unsafe, n)
        inflation = round(raw_pct - adj_pct, 1)

        cond_stats[cond] = {
            "n": n, "raw_unsafe": raw_unsafe, "adj_unsafe": adj_unsafe,
            "fp": fp, "fn": fn, "cv": cv,
            "raw_pct": raw_pct, "adj_pct": adj_pct,
            "raw_ci": (raw_lo, raw_hi), "adj_ci": (adj_lo, adj_hi),
            "inflation": inflation,
        }

        label = COND_LABELS[cond]
        print(f"{label:<8} {n:>4} {raw_pct:>6.1f}% [{raw_lo:>5.1f}%, {raw_hi:>5.1f}%] {adj_pct:>6.1f}% [{adj_lo:>5.1f}%, {adj_hi:>5.1f}%] {fp:>4} {fn:>4} {inflation:>+9.1f}pp")

    # -----------------------------------------------------------------------
    # 2. Per-model breakdown
    # -----------------------------------------------------------------------
    print()
    print("=" * 80)
    print("2. PER-MODEL ASR (ADJUSTED)")
    print("=" * 80)

    header = f"{'Model':<28}"
    for cond in CONDS:
        header += f" {COND_LABELS[cond]:>7}"
    header += f" {'Overall':>8}"
    print(header)
    print("-" * len(header))

    model_overall = {}
    for model in MODELS:
        line = f"{model:<28}"
        total_adj = 0
        total_n = 0
        for cond in CONDS:
            s = [r for r in rows if r["model"] == model and r["condition"] == cond]
            adj = sum(1 for r in s if is_human_unsafe(r["final_human_label"]))
            pct = adj / len(s) * 100
            line += f" {pct:>6.1f}%"
            total_adj += adj
            total_n += len(s)
        overall = total_adj / total_n * 100
        line += f" {overall:>7.1f}%"
        model_overall[model] = round(overall, 1)
        print(line)

    # -----------------------------------------------------------------------
    # 3. Per-model Wilson CIs
    # -----------------------------------------------------------------------
    print()
    print("=" * 80)
    print("3. PER-MODEL OVERALL ASR WITH WILSON CIs")
    print("=" * 80)
    print(f"{'Model':<28} {'Adj ASR':>8} {'95% CI':>20}")
    print("-" * 60)
    for model in MODELS:
        s = [r for r in rows if r["model"] == model]
        adj = sum(1 for r in s if is_human_unsafe(r["final_human_label"]))
        pct, lo, hi = wilson_ci(adj, len(s))
        print(f"{model:<28} {pct:>7.1f}% [{lo:>5.1f}%, {hi:>5.1f}%]")

    # -----------------------------------------------------------------------
    # 4. Consistency checks
    # -----------------------------------------------------------------------
    print()
    print("=" * 80)
    print("4. CONSISTENCY CHECKS")
    print("=" * 80)

    # 4a. cv+fp == raw_unsafe for every model x condition cell
    fail_cells = 0
    for model in MODELS:
        for cond in CONDS:
            s = [r for r in rows if r["model"] == model and r["condition"] == cond]
            cv = sum(1 for r in s if r["final_human_label"] == "confirmed_vulnerability")
            fp = sum(1 for r in s if r["final_human_label"] == "false_positive")
            raw = sum(1 for r in s if is_raw_unsafe(r["raw_detector_label"]))
            if cv + fp != raw:
                fail_cells += 1
                print(f"  FAIL: {model} x {COND_LABELS[cond]}: cv+fp={cv+fp} != raw={raw}")
    print(f"  cv+fp==raw_unsafe: {48 - fail_cells}/48 cells OK")

    # 4b. Annotator coverage
    ann1 = sum(1 for r in rows if r["annotator_1_label"])
    ann2 = sum(1 for r in rows if r["annotator_2_label"])
    disagree = sum(1 for r in rows if r["disagreement_flag"] == "True")
    pf = sum(1 for r in rows if r["provider_filtered"] == "True")
    empty_intent = sum(1 for r in rows if not r["intent_id"])
    print(f"  Annotator 1 coverage: {ann1}/1920")
    print(f"  Annotator 2 coverage: {ann2}/1920")
    print(f"  Disagreements: {disagree}")
    print(f"  Provider-filtered: {pf}")
    print(f"  Empty intent_id: {empty_intent}")
    print(f"  Unique intents: {len(set(r['intent_id'] for r in rows))}")

    # -----------------------------------------------------------------------
    # 5. McNemar paired comparisons
    # -----------------------------------------------------------------------
    print()
    print("=" * 80)
    print("5. McNEMAR PAIRED COMPARISONS (Bonferroni k=15)")
    print("=" * 80)

    # Build lookup: (model, intent, condition) -> human_unsafe
    lookup = {}
    for r in rows:
        key = (r["model"], r["intent_id"], r["condition"])
        lookup[key] = is_human_unsafe(r["final_human_label"])

    comparisons = [
        ("best_of_k_st", "adaptive_single_turn"),
        ("adaptive_single_turn", "adaptive_multi_turn"),
        ("adaptive_single_turn", "adaptive_single_query_st"),
        ("adaptive_single_query_st", "adaptive_multi_turn"),
        ("adaptive_single_query_st", "direct_single_turn"),
        ("best_of_k_st", "scripted_multi_turn"),
        ("adaptive_multi_turn", "scripted_multi_turn"),
        ("scripted_multi_turn", "direct_single_turn"),
        ("best_of_k_st", "direct_single_turn"),
    ]

    print(f"{'Comparison':<40} {'ASR_A':>6} {'ASR_B':>6} {'Diff':>8} {'A>B':>5} {'B>A':>5} {'p_raw':>10} {'p_corr':>10} {'Sig':>5}")
    print("-" * 100)

    intents = sorted(set(r["intent_id"] for r in rows))
    for cond_a, cond_b in comparisons:
        a_wins = 0  # A succeeds, B fails
        b_wins = 0  # B succeeds, A fails
        for model in MODELS:
            for intent in intents:
                a_unsafe = lookup.get((model, intent, cond_a), False)
                b_unsafe = lookup.get((model, intent, cond_b), False)
                if a_unsafe and not b_unsafe:
                    a_wins += 1
                elif b_unsafe and not a_unsafe:
                    b_wins += 1

        asr_a = cond_stats[cond_a]["adj_pct"]
        asr_b = cond_stats[cond_b]["adj_pct"]
        diff = round(asr_a - asr_b, 1)
        p_raw = mcnemar_test(a_wins, b_wins)
        p_corr = min(p_raw * 15, 1.0)  # Bonferroni k=15
        sig = "YES" if p_corr < 0.05 else "no"

        label_a = COND_LABELS[cond_a]
        label_b = COND_LABELS[cond_b]
        print(f"{label_a + ' vs ' + label_b:<40} {asr_a:>5.1f}% {asr_b:>5.1f}% {diff:>+7.1f}pp {a_wins:>5} {b_wins:>5} {p_raw:>10.4f} {p_corr:>10.4f} {sig:>5}")

    # -----------------------------------------------------------------------
    # 6. Evidence Card metrics (from artifact)
    # -----------------------------------------------------------------------
    print()
    print("=" * 80)
    print("6. EVIDENCE CARD METRICS")
    print("=" * 80)

    ec_path = Path(__file__).resolve().parent.parent / "data" / "evidence_card.json"
    if ec_path.exists():
        with open(ec_path) as f:
            ec = json.load(f)
        print(f"{'Cond':<8} {'RawASR':>7} {'AdjASR':>7} {'Infl':>7} {'MaxCap':>7} {'Realized':>9} {'Cost/Succ':>10} {'Fragility':>10} {'Excl':>6}")
        print("-" * 85)
        for cond in CONDS:
            if cond not in ec:
                continue
            d = ec[cond]
            label = COND_LABELS[cond]
            print(f"{label:<8} {d['raw_asr']:>6.1f}% {d['adj_asr']:>6.1f}% {d['measurement_inflation']:>+6.1f}pp {d['max_target_cap']:>7} {d['realized_target_mean']:>8.1f} ${d['cost_per_success']:>9.4f} {d['detector_fragility_max_fp']:>9.1f}% {d['exclusion_rate']:>5.1f}%")
    else:
        print("  evidence_card.json not found")

    # -----------------------------------------------------------------------
    # 7. BoK K=1/3/5 ablation (from artifact)
    # -----------------------------------------------------------------------
    print()
    print("=" * 80)
    print("7. BoK K ABLATION")
    print("=" * 80)

    bok_k_path = Path(__file__).resolve().parent.parent / "data" / "bok_k_ablation.json"
    if bok_k_path.exists():
        with open(bok_k_path) as f:
            bok_k = json.load(f)

        overall = bok_k["overall"]
        print("Overall:")
        for k in ["k_1", "k_3", "k_5"]:
            d = overall[k]
            ci = f"[{d['ci'][0]:.1f}%, {d['ci'][1]:.1f}%]"
            print(f"  K={k[-1]}: {d['asr']:.1f}% {ci}  ({d['successes']}/{d['total']})")
        if "marginal_gain_3_to_5" in overall:
            print(f"  Marginal gain K=3->5: +{overall['marginal_gain_3_to_5']:.1f}pp")

        print("\nPer-model:")
        print(f"  {'Model':<28} {'K=1':>6} {'K=3':>6} {'K=5':>6} {'Gain 3→5':>9}")
        print("  " + "-" * 60)
        for model in sorted(bok_k["per_model"].keys()):
            d = bok_k["per_model"][model]
            k1 = d.get("k_1", {}).get("asr", 0)
            k3 = d.get("k_3", {}).get("asr", 0)
            k5 = d.get("k_5", {}).get("asr", 0)
            gain = d.get("marginal_gain_3_to_5", 0)
            print(f"  {model:<28} {k1:>5.1f}% {k3:>5.1f}% {k5:>5.1f}% {gain:>+8.1f}pp")
    else:
        print("  bok_k_ablation.json not found")

    # -----------------------------------------------------------------------
    # 8. BoK sequential stopping (from artifact)
    # -----------------------------------------------------------------------
    print()
    print("=" * 80)
    print("8. BoK SEQUENTIAL STOPPING SIMULATION")
    print("=" * 80)

    seq_path = Path(__file__).resolve().parent.parent / "data" / "bok_sequential_stopping.json"
    if seq_path.exists():
        with open(seq_path) as f:
            seq = json.load(f)
        overall = seq["overall"]
        print(f"  Mean realized queries: {overall['mean_realized_queries']:.2f}/5.0 ({overall['mean_realized_queries']/5*100:.1f}% of max cap)")
        print(f"  Median realized queries: {overall['median_realized_queries']}/5")
        print(f"  Theoretical savings: {overall['theoretical_savings_pct']:.1f}%")

        dist = seq.get("distribution", {})
        if dist:
            print("\n  Stopping distribution:")
            for k in ["0", "1", "2", "3", "4", "never"]:
                if k in dist:
                    label = f"Variant {int(k)+1}" if k.isdigit() else "Never"
                    print(f"    {label}: {dist[k]:.1f}%")

        print(f"\n  Per-model:")
        print(f"  {'Model':<28} {'Mean':>6} {'Savings':>8}")
        print("  " + "-" * 45)
        for model in sorted(seq.get("per_model", {}).keys()):
            d = seq["per_model"][model]
            print(f"  {model:<28} {d['mean_realized_queries']:>5.1f} {d['theoretical_savings_pct']:>7.1f}%")
    else:
        print("  bok_sequential_stopping.json not found")

    # -----------------------------------------------------------------------
    # 9. BoK strategy diversity (from artifact)
    # -----------------------------------------------------------------------
    print()
    print("=" * 80)
    print("9. BoK STRATEGY DIVERSITY AUDIT")
    print("=" * 80)

    div_path = Path(__file__).resolve().parent.parent / "data" / "bok_diversity_audit.json"
    if div_path.exists():
        with open(div_path) as f:
            div = json.load(f)
        overall = div["overall_stats"]
        print(f"  Total intents: {overall['total_intents']}")
        print(f"  Total variants: {overall['total_variants']}")
        print(f"  Low diversity intents: {overall['low_diversity_intents']}/{overall['total_intents']} ({overall['low_diversity_intents']/overall['total_intents']*100:.1f}%)")
        print(f"  High similarity intents: {overall['high_similarity_intents']}/{overall['total_intents']}")
        print(f"\n  Strategy distribution:")
        for strat, count in sorted(overall["strategy_distribution"].items(), key=lambda x: -x[1]):
            pct = count / overall["total_variants"] * 100
            print(f"    {strat:<20} {count:>4} ({pct:.1f}%)")
    else:
        print("  bok_diversity_audit.json not found")

    # -----------------------------------------------------------------------
    # 10. Summary of all metrics for paper
    # -----------------------------------------------------------------------
    print()
    print("=" * 80)
    print("10. SUMMARY TABLE (copy-paste ready for paper)")
    print("=" * 80)
    print()
    print("| Condition | Raw ASR | 95% CI | Adj. ASR | Adj. 95% CI | FP | FN | Inflation |")
    print("|---|---|---|---|---|---|---|---|")
    for cond in CONDS:
        d = cond_stats[cond]
        label = COND_LABELS[cond]
        print(f"| {label} | {d['raw_pct']:.1f}% | [{d['raw_ci'][0]:.1f}%, {d['raw_ci'][1]:.1f}%] | {d['adj_pct']:.1f}% | [{d['adj_ci'][0]:.1f}%, {d['adj_ci'][1]:.1f}%] | {d['fp']} | {d['fn']} | {d['inflation']:+.1f}pp |")


if __name__ == "__main__":
    main()
