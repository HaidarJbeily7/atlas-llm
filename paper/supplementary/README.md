# ATLAS Supplementary Materials

Supplementary materials for: *Disentangling Attack Mechanisms in Automated LLM Red-Teaming: A Structured Ablation Study with Human-Validated Measurements*

## Directory Structure

```text
supplementary/
  README.md                            # This file
  LICENSE                              # MIT (code) + CC BY 4.0 (data)
  requirements.txt                     # Python dependencies
  data/                                # Anonymized human-review labels and aggregate analysis outputs
    annotation_ledger.csv              # All 1,920 human-reviewed findings (anonymized; no annotator names)
    annotation_rubric.md               # Binary-verdict rubric used by human annotators (Appendix E)
    intent_list.md                     # The 40 harm intents, grouped by category (Appendix I)
    evidence_card.{json,md}            # Per-condition metrics (raw/adj ASR, FP/FN, cost)
    mechanism_decomposition.{json,md}  # Logistic regression results (ORs, AMEs, CIs)
    success_vs_budget.{json,md}        # K=1..5 budget curves
    human_validation_counterfactual.{json,md}  # Six conclusions that flip without human review
    bok_k_ablation.json                # BoK K-ablation curves
    bok_sequential_stopping.json       # Sequential-stopping simulation
    bok_diversity_audit.json           # BoK strategy diversity validation
    detector_performance.json          # Per-detector P/R/F1 across all conditions
  scripts/
    reproduce_all.py                   # Master check: verifies every paper number; prints PASS/FAIL summary
    compute_kappa.py                   # FP/FN counts, per-condition ASR, label distribution
    verify_final_answers.py            # Detailed verification with Wilson CIs, McNemar, BoK budget curves
    mechanism_decomposition.py         # Re-fits the fixed-effects logistic regression
    check_detector_performance.py      # Prints detector P/R/F1 tables and verifies F1-range claims
  figures_src/
    generate_figures.py                # Appendix budget-curve figures
    generate_visual_abstract.py        # Inline panels A, B, C
```

## Anonymization

The annotation ledger has been **anonymized** prior to release:

- Annotator-identifying columns (`annotator_1_author`, `annotator_2_author`) have been **removed**.
- Only the label columns (`annotator_1_label`, `annotator_2_label`) and adjudication outcome are retained.
- All other personal or institutional identifiers have been stripped.

Raw experiment artifacts (model outputs, attacker prompt corpora, SQL backups) are **not released** to avoid distributing harmful content. The aggregate JSON files in `data/` were derived from those artifacts and are sufficient to reproduce every quantitative claim in the paper.

## Quick Start

```bash
python3 scripts/reproduce_all.py
```

Expected output: `52 PASS / 0 FAIL`. The master script verifies:

- Dataset invariants (N, models, intents, conditions, cell balance, double-annotation coverage)
- Per-condition raw + adjusted ASR + FP/FN counts (Tables 1, 3)
- BoK measurement paradox: +5.6pp inflation, +6.2pp raw lead → −0.3pp adjusted (§6)
- Mechanism regression: ORs, AMEs, p-values, McFadden R² (Table 2)
- Variance decomposition: mechanism 22.2%, model 5.0%, intent 6.7% (§5)
- Feedback × multi-turn interaction OR = 0.04 (§5)
- Cost-per-success: PAIR-1 $0.011, PAIR-5 $0.016 (§4.1)
- BoK K-ablation: K=1 56.2%, K=3 84.1%, K=5 91.2% (§6)
- Detector F1 range 59.7%–99.4%; keyword recall 44.0% on BoK-ST; Safety Judge precision 77.7% on SS-MT (Tables 4, 6)

## Detailed Scripts

| Script | Reproduces |
|---|---|
| `reproduce_all.py` | Master PASS/FAIL summary covering all of the above |
| `compute_kappa.py` | FP/FN counts, per-condition ASR, label distribution |
| `verify_final_answers.py` | Wilson CIs, McNemar comparisons, BoK sequential-stopping, copy-pastable summary table |
| `mechanism_decomposition.py` | Re-fits M0–M6 GEE logistic regression with block-bootstrap CIs (n_boot=2000 by default; `--n-boot 200` for a quick sanity check) |
| `check_detector_performance.py` | Prints all P/R/F1 tables and verifies the detector-extreme claims |

All scripts resolve paths via `Path(__file__).parent.parent / "data"`, so they run from any working directory with no arguments.

## Annotation Ledger Schema

`data/annotation_ledger.csv` — 1,920 rows × 12 columns:

| Column | Description |
|---|---|
| `finding_id` | Unique identifier for the (model, intent, condition) finding |
| `model` | Target LLM (e.g., `claude-sonnet-4`, `gpt-4o`) |
| `intent_id` | Harm intent (e.g., `intent-bioweapon`) |
| `condition` | One of the 6 experimental conditions |
| `raw_detector_label` | Aggregated automated verdict (`safe` / `unsafe`) |
| `annotator_1_label`, `annotator_2_label` | Independent human labels |
| `adjudication_status` | `agreed` or `adjudicated` |
| `final_human_label` | Post-adjudication consensus |
| `severity` | Harm severity tier |
| `disagreement_flag` | Boolean: did annotators disagree? |
| `provider_filtered` | Boolean: was the response provider-filtered? |

### Note on Inter-Annotator Agreement

The released ledger contains **post-adjudication** consensus labels, so it shows 0 disagreements. The paper's Cohen's κ = 0.81 and ~12% disagreement rate were computed from the annotation platform's **pre-adjudication** raw labels, which contain individual annotator decisions before consensus resolution and are not in the released ledger (to keep annotator identities out of the supplementary). The post-adjudication labels in the released ledger are the ground truth used for all FP/FN counts and adjusted-ASR computations in the paper.

## Requirements

Python 3.10 — 3.13. Install dependencies via:

```bash
pip install -r requirements.txt
```

See `requirements.txt` for pinned minimum versions.

## License

- **Code** (`scripts/`, `figures_src/`) — MIT
- **Data** (`data/`) — CC BY 4.0

See `LICENSE` for full text and the responsible-use note.
