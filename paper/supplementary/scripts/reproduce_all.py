#!/usr/bin/env python3
"""Master reproducibility check for the ATLAS supplementary.

Loads every aggregate artifact and the anonymized annotation ledger, recomputes
each headline number, and prints a PASS/FAIL line for every quantitative claim
in the paper that is reproducible from the released materials.

Run from any directory:
    python3 scripts/reproduce_all.py
"""
from __future__ import annotations

import csv
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"

CONDS = ["direct_single_turn", "scripted_multi_turn", "adaptive_single_query_st",
         "adaptive_single_turn", "adaptive_multi_turn", "best_of_k_st"]
COND_LABEL = {
    "direct_single_turn": "OSS-ST", "scripted_multi_turn": "SS-MT",
    "adaptive_single_query_st": "ASQ-ST", "adaptive_single_turn": "AMQ-ST",
    "adaptive_multi_turn": "AMQ-MT", "best_of_k_st": "BoK-ST",
}

# ---------------------------------------------------------------------------
# Result-tracking
# ---------------------------------------------------------------------------
_results: list[tuple[bool, str, str]] = []  # (pass, claim, observation)


def check(passes: bool, claim: str, observation: str) -> None:
    _results.append((passes, claim, observation))


def report() -> int:
    n_pass = sum(1 for p, _, _ in _results if p)
    n_fail = len(_results) - n_pass
    print()
    print("=" * 80)
    print(f"REPRODUCIBILITY SUMMARY  —  {n_pass} PASS  /  {n_fail} FAIL  ({len(_results)} total)")
    print("=" * 80)
    for ok, claim, obs in _results:
        flag = "PASS" if ok else "FAIL"
        print(f"  [{flag}] {claim}")
        print(f"         → {obs}")
    return 0 if n_fail == 0 else 1


def close(observed: float, expected: float, tol: float = 0.05) -> bool:
    return abs(observed - expected) <= tol


# ---------------------------------------------------------------------------
# Ledger-based checks
# ---------------------------------------------------------------------------
def load_ledger() -> list[dict]:
    with open(DATA / "annotation_ledger.csv") as f:
        return list(csv.DictReader(f))


def check_dataset_invariants(rows: list[dict]) -> None:
    n = len(rows)
    check(n == 1920, "N = 1,920 findings", f"got N = {n}")

    models = sorted({r["model"] for r in rows})
    check(len(models) == 8, "8 target models", f"found {len(models)}: {', '.join(models)}")

    intents = sorted({r["intent_id"] for r in rows})
    check(len(intents) == 40, "40 harm intents", f"found {len(intents)} intents")

    conditions = sorted({r["condition"] for r in rows})
    check(len(conditions) == 6, "6 conditions", f"found {len(conditions)}: {', '.join(conditions)}")

    # Cell balance
    cells = Counter((r["model"], r["condition"]) for r in rows)
    balanced = all(v == 40 for v in cells.values())
    check(balanced, "Every (model, condition) cell has 40 intents",
          f"min={min(cells.values())}, max={max(cells.values())}")

    # Double annotation
    double = sum(1 for r in rows if r["annotator_1_label"] and r["annotator_2_label"])
    check(double == n, "100% double-annotation coverage",
          f"{double}/{n} double-annotated")


def per_condition_asr(rows: list[dict]) -> dict[str, dict[str, float]]:
    by_cond = defaultdict(list)
    for r in rows:
        by_cond[r["condition"]].append(r)
    out = {}
    for cond, cond_rows in by_cond.items():
        n = len(cond_rows)
        raw_pos = sum(1 for r in cond_rows if r["raw_detector_label"] == "unsafe")
        adj_pos = sum(
            1 for r in cond_rows
            if r["final_human_label"] in ("confirmed_vulnerability", "false_negative")
        )
        out[cond] = {
            "n": n,
            "raw": raw_pos / n * 100,
            "adj": adj_pos / n * 100,
            "fp": sum(1 for r in cond_rows if r["final_human_label"] == "false_positive"),
            "fn": sum(1 for r in cond_rows if r["final_human_label"] == "false_negative"),
        }
    return out


# Expected per-condition ASR from the paper
PAPER_COND_ASR = {
    "direct_single_turn":       {"raw": 15.9, "adj": 14.4, "fp": 5,  "fn": 0},
    "scripted_multi_turn":      {"raw": 51.2, "adj": 37.5, "fp": 51, "fn": 7},
    "adaptive_single_query_st": {"raw": 64.1, "adj": 63.7, "fp": 4,  "fn": 3},
    "adaptive_single_turn":     {"raw": 85.0, "adj": 85.9, "fp": 5,  "fn": 8},
    "adaptive_multi_turn":      {"raw": 63.4, "adj": 63.4, "fp": 21, "fn": 21},
    "best_of_k_st":             {"raw": 91.2, "adj": 85.6, "fp": 23, "fn": 5},
}


def check_per_condition(asr: dict) -> None:
    for cond, expected in PAPER_COND_ASR.items():
        obs = asr[cond]
        label = COND_LABEL[cond]
        check(close(obs["raw"], expected["raw"], 0.1),
              f"{label} raw ASR = {expected['raw']:.1f}%",
              f"observed {obs['raw']:.1f}%")
        check(close(obs["adj"], expected["adj"], 0.1),
              f"{label} adjusted ASR = {expected['adj']:.1f}%",
              f"observed {obs['adj']:.1f}%")
        check(obs["fp"] == expected["fp"] and obs["fn"] == expected["fn"],
              f"{label} FP/FN = {expected['fp']}/{expected['fn']}",
              f"observed FP={obs['fp']}, FN={obs['fn']}")


def check_bok_paradox(asr: dict) -> None:
    bok = asr["best_of_k_st"]
    pair = asr["adaptive_single_turn"]
    inflation = bok["raw"] - bok["adj"]
    check(close(inflation, 5.6, 0.1),
          "BoK measurement paradox: inflation = +5.6pp",
          f"observed {inflation:+.1f}pp (raw {bok['raw']:.1f}% → adj {bok['adj']:.1f}%)")
    delta_raw = bok["raw"] - pair["raw"]
    delta_adj = bok["adj"] - pair["adj"]
    check(close(delta_raw, 6.2, 0.2),
          "BoK leads PAIR-5 by +6.2pp raw",
          f"observed {delta_raw:+.1f}pp")
    check(abs(delta_adj) <= 1.0,
          "BoK ≈ PAIR-5 after human review (|Δ| ≤ 1pp)",
          f"observed Δ = {delta_adj:+.1f}pp")


# ---------------------------------------------------------------------------
# Aggregate-JSON checks
# ---------------------------------------------------------------------------
def check_mechanism_regression() -> None:
    path = DATA / "mechanism_decomposition.json"
    d = json.loads(path.read_text())
    m4 = d["model_results"]["M4_primary"]
    var = d["variance_decomposition"]

    # Mechanism point estimates from bootstrap (paper Table 2 AMEs)
    boot = d["bootstrap_marginal_effects"]
    expected_ame = {
        "attacker_llm": 36.6,
        "diversity":    22.4,
        "feedback":     10.2,
        "multi_turn":    0.3,
    }
    for mech, exp_ame in expected_ame.items():
        obs = boot[mech]["ame_mean"]
        check(close(obs, exp_ame, 0.5),
              f"{mech} AME = {exp_ame:+.1f}pp",
              f"observed {obs:+.2f}pp (bootstrap mean)")
    # Odds ratios from M4 primary
    expected_or = {
        "attacker_llm": 8.30,
        "diversity":    4.99,
        "feedback":     1.98,
        "multi_turn":   1.02,
    }
    coefs = m4.get("mechanisms", {})
    for mech, exp_or in expected_or.items():
        if mech in coefs and "odds_ratio" in coefs[mech]:
            obs_or = coefs[mech]["odds_ratio"]
            check(close(obs_or, exp_or, 0.05),
                  f"{mech} OR = {exp_or:.2f}",
                  f"observed {obs_or:.3f}")
    # p-value for multi-turn (paper: .885)
    if "multi_turn" in coefs:
        obs_p = coefs["multi_turn"].get("p_value")
        if obs_p is not None:
            check(close(obs_p, 0.885, 0.005),
                  "Multi-turn p-value = .885",
                  f"observed {obs_p:.4f}")

    check(close(m4["pseudo_r2"], 0.344, 0.005),
          "McFadden R² = 0.344 (M4 primary)",
          f"observed {m4['pseudo_r2']:.4f}")

    check(close(var["mechanism_effect"]["pseudo_r2"], 22.2, 0.1),
          "Mechanism deviance explained = 22.2%",
          f"observed {var['mechanism_effect']['pseudo_r2']:.2f}%")
    check(close(var["model_effect"]["pseudo_r2"], 5.0, 0.1),
          "Target-model deviance explained = 5.0%",
          f"observed {var['model_effect']['pseudo_r2']:.2f}%")
    check(close(var["intent_effect"]["pseudo_r2"], 6.7, 0.1),
          "Intent deviance explained = 6.7%",
          f"observed {var['intent_effect']['pseudo_r2']:.2f}%")

    m5 = d["model_results"].get("M5_interaction")
    if m5:
        check(close(m5["interaction_or"], 0.04, 0.01),
              "Feedback×MT interaction OR = 0.04",
              f"observed {m5['interaction_or']:.3f}")


def check_evidence_card() -> None:
    ec = json.loads((DATA / "evidence_card.json").read_text())
    # PAIR-1 (ASQ-ST) cost/success
    asq = ec["adaptive_single_query_st"]
    check(close(asq["cost_per_success"], 0.011, 0.001),
          "PAIR-1 (ASQ-ST) cost-per-success = $0.011",
          f"observed ${asq['cost_per_success']:.4f}")
    # PAIR-5 (AMQ-ST)
    amq_st = ec["adaptive_single_turn"]
    check(close(amq_st["cost_per_success"], 0.016, 0.001),
          "PAIR-5 (AMQ-ST) cost-per-success = $0.016",
          f"observed ${amq_st['cost_per_success']:.4f}")
    # PAIR-5 realized target queries (mean 1.6)
    check(close(amq_st["realized_target_mean"], 1.6, 0.1),
          "PAIR-5 realized target queries: mean 1.6",
          f"observed {amq_st['realized_target_mean']:.2f}")


def check_bok_k_ablation() -> None:
    d = json.loads((DATA / "bok_k_ablation.json").read_text())
    overall = d["overall"]
    # Paper claims: K=1: 56.2%, K=3: 84.1%, K=5: 91.2%; marginal K=3→5 = +7.2pp
    for k, exp in [(1, 56.2), (3, 84.1), (5, 91.2)]:
        obs = overall[f"k_{k}"]["asr"]
        check(close(obs, exp, 0.1),
              f"BoK raw ASR at K={k} = {exp:.1f}%",
              f"observed {obs:.2f}%")
    obs_gain = overall["marginal_gain_3_to_5"]
    check(close(obs_gain, 7.2, 0.1),
          "BoK marginal gain K=3→5 = +7.2pp",
          f"observed {obs_gain:+.2f}pp")


def check_detector_performance() -> None:
    d = json.loads((DATA / "detector_performance.json").read_text())
    s = d["summary"]
    check(close(s["min_f1"], 59.7, 0.1),
          "Minimum detector F1 = 59.7% (keyword × BoK-ST, paper §1)",
          f"observed {s['min_f1']:.2f}% [{s['min_f1_pair']}]")
    check(close(d["keyword"]["best_of_k_st"]["recall"], 44.0, 0.1),
          "Keyword recall on BoK-ST = 44.0% (§4.2)",
          f"observed {d['keyword']['best_of_k_st']['recall']:.2f}%")
    check(close(d["safety_judge"]["scripted_multi_turn"]["precision"], 77.7, 0.1),
          "Safety Judge precision on SS-MT = 77.7% (§4.2)",
          f"observed {d['safety_judge']['scripted_multi_turn']['precision']:.2f}%")
    # Safety Judge F1 ≥ 87% across all conditions
    sj_min = min(v["f1"] for v in d["safety_judge"].values())
    check(sj_min >= 87.0,
          "Safety Judge F1 ≥ 87% across all conditions (Finding 26)",
          f"observed min Safety Judge F1 = {sj_min:.2f}%")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> int:
    print(f"ATLAS supplementary reproducibility check\n  root: {ROOT}\n  data: {DATA}\n")
    rows = load_ledger()

    print("[1/5] Dataset invariants...")
    check_dataset_invariants(rows)

    print("[2/5] Per-condition ASR + FP/FN counts...")
    asr = per_condition_asr(rows)
    check_per_condition(asr)
    check_bok_paradox(asr)

    print("[3/5] Mechanism regression (Table 2)...")
    check_mechanism_regression()

    print("[4/5] Cost-efficiency (evidence card)...")
    check_evidence_card()
    check_bok_k_ablation()

    print("[5/5] Detector P/R/F1 (Tables 4, 6)...")
    check_detector_performance()

    return report()


if __name__ == "__main__":
    sys.exit(main())
