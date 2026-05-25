#!/usr/bin/env python3
"""Print detector P/R/F1 from supplementary/data/detector_performance.json and
verify the paper's headline detector claims.

Reproduces:
  * Table 4 (Detector extremes)
  * Appendix Table 6 (Full detector performance)
  * Section 1 / 4.2 claims about detector F1 range and failure modes
"""
from __future__ import annotations

import json
from pathlib import Path


DATA = Path(__file__).resolve().parent.parent / "data" / "detector_performance.json"

DETECTORS = ["safety_judge", "semantic_judge", "llm_judge", "keyword", "refusal"]
COND_LABELS = {
    "direct_single_turn": "OSS-ST",
    "scripted_multi_turn": "SS-MT",
    "adaptive_single_query_st": "ASQ-ST",
    "adaptive_single_turn": "AMQ-ST",
    "adaptive_multi_turn": "AMQ-MT",
    "best_of_k_st": "BoK-ST",
}


def main() -> None:
    perf = json.loads(DATA.read_text())

    print("=" * 78)
    print("DETECTOR PERFORMANCE (P/R/F1 vs human ground truth)")
    print("=" * 78)
    for det in DETECTORS:
        rows = perf[det]
        print(f"\n  {det.replace('_', ' ').title()}")
        print(f"    {'Condition':10s}  {'P':>6}  {'R':>6}  {'F1':>6}")
        # Sort by F1 descending
        sorted_rows = sorted(rows.items(), key=lambda kv: -kv[1]["f1"])
        for cond, m in sorted_rows:
            print(f"    {COND_LABELS[cond]:10s}  {m['precision']:6.2f}  {m['recall']:6.2f}  {m['f1']:6.2f}")

    print("\n" + "=" * 78)
    print("PAPER CLAIM VERIFICATION")
    print("=" * 78)
    s = perf["summary"]
    checks = [
        ("F1 range 59.7%-99.4% (paper §1)",
         f"min F1 = {s['min_f1']:.2f} ({s['min_f1_pair']}); max F1 = {s['max_f1']:.2f} ({s['max_f1_pair']})"),
        ("Safety Judge F1 > 87% across all conditions (Finding 26)",
         f"Safety Judge min F1 = {s['safety_judge_min_f1']:.2f}"),
        ("Safety Judge precision drops to 77.7% on SS-MT (§4.2)",
         f"safety_judge.SS-MT precision = {s['safety_judge_min_precision_on_ss_mt']:.2f}"),
        ("Keyword recall drops to 44.0% on BoK-ST (§4.2)",
         f"keyword.BoK-ST recall = {s['keyword_min_recall_on_bok_st']:.2f}"),
    ]
    for claim, result in checks:
        print(f"  {claim}")
        print(f"    → {result}")


if __name__ == "__main__":
    main()
