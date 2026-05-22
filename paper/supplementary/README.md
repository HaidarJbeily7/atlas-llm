# ATLAS Supplementary Materials

Supplementary materials for: *Disentangling Attack Mechanisms in Automated LLM Red-Teaming: A Factorial Study with Human-Validated Measurements*

## Directory Structure

```
supplementary/
  data/                          # Experiment data and artifacts
    annotation_ledger.csv        # All 1,920 human-reviewed findings
    evidence_card.{json,md}      # Per-condition metrics (raw/adj ASR, FP/FN, cost)
    mechanism_decomposition.{json,md}  # Logistic regression results (ORs, AMEs, CIs)
    success_vs_budget.{json,md}  # K=1..5 budget curves (PAIR-5, BoK, i.i.d.)
    human_validation_counterfactual.{json,md}  # Six wrong conclusions without human review
  scripts/                       # Analysis and verification scripts
    compute_kappa.py             # Cohen's kappa, FP/FN counts, annotation coverage
    recompute_with_uncertainty.py # Wilson CIs and McNemar's paired tests
    verify_final_answers.py      # Verifies all claims against annotation_ledger.csv
    mechanism_decomposition.py   # Fixed-effects logistic regression + bootstrap CIs
    success_vs_budget.py         # Budget curves and 3-quantity decomposition
    human_validation_counterfactual.py  # Raw vs validated comparison
    generate_evidence_card.py    # Per-condition metric table generation
    export_annotation_ledger.py  # Exports ledger from annotation platform DB
    bok_k_ablation.py            # K=1..5 ablation for BoK
    bok_sequential_stopping.py   # Sequential stopping analysis
    audit_bok_diversity.py       # Validates 5 distinct strategies per intent
  figures_src/                   # Figure generation scripts
    generate_figures.py          # Appendix figures (budget curves)
    generate_visual_abstract.py  # Inline figures (panels A, B, C)
```

## Annotation Ledger

`data/annotation_ledger.csv` contains all 1,920 findings with columns:
- `finding_id`, `model`, `intent_id`, `condition`
- `raw_detector_label` (automated verdict)
- `annotator_1_label`, `annotator_2_label` (independent human labels)
- `adjudication_status`, `final_human_label` (post-adjudication consensus)
- `severity`, `disagreement_flag`

Inter-annotator agreement: Cohen's kappa = 0.81. Run `scripts/compute_kappa.py` to verify.

## Reproducing Results

All scripts read from `data/annotation_ledger.csv`. To verify the paper's claims:

```bash
python scripts/compute_kappa.py           # Table 2: FP/FN counts
python scripts/recompute_with_uncertainty.py  # Tables 2-3: ASR with CIs
python scripts/mechanism_decomposition.py     # Table 5: regression coefficients
python scripts/success_vs_budget.py           # Table 9: budget curves
python scripts/verify_final_answers.py        # Cross-checks all quantitative claims
```

## Requirements

Python 3.10+, numpy, scipy, pandas, statsmodels, matplotlib.
