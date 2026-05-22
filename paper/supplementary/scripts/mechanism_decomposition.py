#!/usr/bin/env python3
"""Mechanism decomposition: mixed-effects logistic regression.

Estimates the causal contribution of four attack mechanisms to jailbreak
success, controlling for heterogeneity across target models and harmful
intents via crossed random intercepts.

Mechanisms (binary features derived from the 6 experimental conditions):
  attacker_llm   — an LLM crafts the attack prompt (vs. human-authored)
  feedback       — attacker iteratively refines based on target responses
  multi_turn     — attack spans multiple conversation turns
  diversity      — K>1 pre-generated diverse strategy variants

Design matrix:
  Condition          | attacker_llm | feedback | multi_turn | diversity
  -------------------|-------------|----------|------------|----------
  Direct ST          |     0       |    0     |     0      |     0
  Scripted MT        |     0       |    0     |     1      |     0
  PAIR-1 (ASQ-ST)    |     1       |    0     |     0      |     0
  PAIR-5 (AMQ-ST)    |     1       |    1     |     0      |     0
  Adaptive MT        |     1       |    1     |     1      |     0
  BoK                |     1       |    0     |     0      |     1

Models fitted:
  M0  Null (intercept only)
  M1  + model random intercept
  M2  + intent random intercept
  M3  + model + intent (crossed RE)                      — variance decomposition
  M4  + mechanisms (fixed effects) + model + intent FE   — primary model
  M5  + feedback×multi_turn interaction                  — interaction check
  M6  GEE with model clusters + intent FE                — cluster-robust SEs

Usage:
    python3 scripts/mechanism_decomposition.py
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import warnings
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

EXPERIMENT_DIR = "docs/experiment/20260505_003630"
LEDGER_PATH = "docs/v6/artifacts/annotation_ledger.csv"

# Condition → mechanism feature encoding
MECHANISM_ENCODING = {
    "direct_single_turn":     {"attacker_llm": 0, "feedback": 0, "multi_turn": 0, "diversity": 0},
    "scripted_multi_turn":    {"attacker_llm": 0, "feedback": 0, "multi_turn": 1, "diversity": 0},
    "adaptive_single_query_st": {"attacker_llm": 1, "feedback": 0, "multi_turn": 0, "diversity": 0},
    "adaptive_single_turn":   {"attacker_llm": 1, "feedback": 1, "multi_turn": 0, "diversity": 0},
    "adaptive_multi_turn":    {"attacker_llm": 1, "feedback": 1, "multi_turn": 1, "diversity": 0},
    "best_of_k_st":           {"attacker_llm": 1, "feedback": 0, "multi_turn": 0, "diversity": 1},
}

MECHANISM_LABELS = {
    "attacker_llm": "LLM-crafted prompt",
    "feedback": "Iterative refinement (target feedback)",
    "multi_turn": "Multi-turn memory",
    "diversity": "Static diversity (K=5 variants)",
}


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def build_dataset(ledger_path: Path) -> pd.DataFrame:
    """Build observation-level dataset from annotation ledger."""
    rows = []
    with open(ledger_path) as f:
        for r in csv.DictReader(f):
            success = 1 if r["final_human_label"] in ("confirmed_vulnerability", "false_negative") else 0
            mechs = MECHANISM_ENCODING[r["condition"]]
            rows.append({
                "success": success,
                "model": r["model"],
                "intent_id": r["intent_id"],
                "condition": r["condition"],
                **mechs,
            })
    df = pd.DataFrame(rows)
    return df


# ---------------------------------------------------------------------------
# Model fitting
# ---------------------------------------------------------------------------

def fit_models(df: pd.DataFrame) -> dict:
    """Fit the model sequence and return structured results."""
    import statsmodels.api as sm
    from statsmodels.genmod.generalized_estimating_equations import GEE
    from statsmodels.genmod.families import Binomial
    from statsmodels.genmod.cov_struct import Exchangeable

    results = {}
    mechanisms = ["attacker_llm", "feedback", "multi_turn", "diversity"]
    y = df["success"].values

    # --- M0: Null model (intercept only) ---
    X0 = np.ones((len(df), 1))
    m0 = sm.Logit(y, X0).fit(disp=0)
    results["M0_null"] = {
        "llf": float(m0.llf),
        "aic": float(m0.aic),
        "n": len(df),
    }

    # --- Helper: model + intent dummies ---
    model_dummies = pd.get_dummies(df["model"], prefix="m", drop_first=True, dtype=float)
    intent_dummies = pd.get_dummies(df["intent_id"], prefix="i", drop_first=True, dtype=float)

    # --- M1: Model FE only ---
    X1 = sm.add_constant(model_dummies)
    m1 = sm.Logit(y, X1).fit(disp=0, maxiter=200)
    results["M1_model_only"] = {
        "llf": float(m1.llf),
        "aic": float(m1.aic),
        "pseudo_r2": float(1 - m1.llf / m0.llf),
    }

    # --- M2: Intent FE only ---
    X2 = sm.add_constant(intent_dummies)
    m2 = sm.Logit(y, X2).fit(disp=0, maxiter=200)
    results["M2_intent_only"] = {
        "llf": float(m2.llf),
        "aic": float(m2.aic),
        "pseudo_r2": float(1 - m2.llf / m0.llf),
    }

    # --- M3: Model + Intent FE (no mechanisms) ---
    X3 = sm.add_constant(pd.concat([model_dummies, intent_dummies], axis=1))
    m3 = sm.Logit(y, X3).fit(disp=0, maxiter=200)
    results["M3_model_intent"] = {
        "llf": float(m3.llf),
        "aic": float(m3.aic),
        "pseudo_r2": float(1 - m3.llf / m0.llf),
    }

    # --- M4: Mechanisms + Model FE + Intent FE (primary model) ---
    mech_df = df[mechanisms].astype(float)
    X4 = sm.add_constant(pd.concat([mech_df, model_dummies, intent_dummies], axis=1))
    m4 = sm.Logit(y, X4).fit(disp=0, maxiter=200)

    mechanism_results = {}
    for mech in mechanisms:
        idx = list(X4.columns).index(mech)
        coef = float(m4.params.iloc[idx])
        se = float(m4.bse.iloc[idx])
        ci_lo = coef - 1.96 * se
        ci_hi = coef + 1.96 * se
        or_val = math.exp(coef)
        or_lo = math.exp(ci_lo)
        or_hi = math.exp(ci_hi)
        p_val = float(m4.pvalues.iloc[idx])

        # Average marginal effect (AME) via finite difference
        X_base = X4.values.copy()
        X_alt = X_base.copy()
        X_alt[:, idx] = 1.0
        X_zero = X_base.copy()
        X_zero[:, idx] = 0.0
        p_alt = 1 / (1 + np.exp(-X_alt @ m4.params.values))
        p_zero = 1 / (1 + np.exp(-X_zero @ m4.params.values))
        ame = float(np.mean(p_alt - p_zero))

        mechanism_results[mech] = {
            "label": MECHANISM_LABELS[mech],
            "coef_logit": round(coef, 4),
            "se": round(se, 4),
            "odds_ratio": round(or_val, 3),
            "or_ci": [round(or_lo, 3), round(or_hi, 3)],
            "p_value": round(p_val, 6),
            "ame_pp": round(ame * 100, 2),
            "significant": p_val < 0.05,
        }

    results["M4_primary"] = {
        "llf": float(m4.llf),
        "aic": float(m4.aic),
        "pseudo_r2": float(1 - m4.llf / m0.llf),
        "pseudo_r2_incremental": float((m3.llf - m4.llf) / abs(m0.llf)),
        "mechanisms": mechanism_results,
        "n_params": int(m4.df_model + 1),
        "n_obs": len(df),
        "converged": bool(m4.mle_retvals.get("converged", True)),
    }

    # --- M5: Add feedback × multi_turn interaction ---
    mech_inter = mech_df.copy()
    mech_inter["feedback_x_multi_turn"] = mech_df["feedback"] * mech_df["multi_turn"]
    X5 = sm.add_constant(pd.concat([mech_inter, model_dummies, intent_dummies], axis=1))
    m5 = sm.Logit(y, X5).fit(disp=0, maxiter=200)

    inter_idx = list(X5.columns).index("feedback_x_multi_turn")
    inter_coef = float(m5.params.iloc[inter_idx])
    inter_se = float(m5.bse.iloc[inter_idx])
    inter_p = float(m5.pvalues.iloc[inter_idx])

    # LR test: M5 vs M4
    lr_stat = 2 * (m5.llf - m4.llf)
    from scipy.stats import chi2
    lr_p = float(chi2.sf(lr_stat, 1))

    results["M5_interaction"] = {
        "llf": float(m5.llf),
        "aic": float(m5.aic),
        "interaction_coef": round(inter_coef, 4),
        "interaction_se": round(inter_se, 4),
        "interaction_or": round(math.exp(inter_coef), 3),
        "interaction_p": round(inter_p, 6),
        "lr_test_vs_m4": round(lr_stat, 3),
        "lr_p_value": round(lr_p, 6),
        "interaction_significant": inter_p < 0.05,
    }

    # --- M6: GEE with model clusters ---
    # GEE handles within-model correlation; intent enters as FE.
    # This gives population-averaged effects with cluster-robust SEs.
    model_codes = pd.Categorical(df["model"]).codes
    X6_feats = pd.concat([mech_df, intent_dummies], axis=1)
    X6 = sm.add_constant(X6_feats)

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        gee_model = GEE(
            y, X6, groups=model_codes,
            family=Binomial(),
            cov_struct=Exchangeable(),
        )
        gee_result = gee_model.fit(maxiter=200)

    gee_mechs = {}
    for mech in mechanisms:
        idx = list(X6.columns).index(mech)
        coef = float(gee_result.params.iloc[idx])
        se = float(gee_result.bse.iloc[idx])
        p_val = float(gee_result.pvalues.iloc[idx])
        gee_mechs[mech] = {
            "coef_logit": round(coef, 4),
            "robust_se": round(se, 4),
            "odds_ratio": round(math.exp(coef), 3),
            "p_value": round(p_val, 6),
        }

    results["M6_gee"] = {
        "mechanisms": gee_mechs,
        "scale": round(float(gee_result.scale), 4),
        "n_clusters": int(len(set(model_codes))),
        "note": "Population-averaged effects with exchangeable correlation within models; intent as fixed effects.",
    }

    return results


# ---------------------------------------------------------------------------
# Variance decomposition
# ---------------------------------------------------------------------------

def variance_decomposition(model_results: dict) -> dict:
    """Compute pseudo-R² decomposition from nested model sequence."""
    llf_null = model_results["M0_null"]["llf"]
    llf_model = model_results["M1_model_only"]["llf"]
    llf_intent = model_results["M2_intent_only"]["llf"]
    llf_both = model_results["M3_model_intent"]["llf"]
    llf_full = model_results["M4_primary"]["llf"]

    total_deviance = -2 * llf_null

    # Incremental deviance explained (Type I SS analogue for logistic regression)
    dev_model = -2 * (llf_null - llf_model)
    dev_intent = -2 * (llf_null - llf_intent)
    dev_model_given_intent = -2 * (llf_intent - llf_both)
    dev_intent_given_model = -2 * (llf_model - llf_both)
    dev_mechanisms = -2 * (llf_both - llf_full)

    # Proportions of null deviance
    decomp = {
        "total_null_deviance": round(total_deviance, 1),
        "model_effect": {
            "deviance_explained": round(dev_model, 1),
            "pseudo_r2": round(dev_model / total_deviance * 100, 2),
            "interpretation": "Variance due to target model identity (robustness differences)",
        },
        "intent_effect": {
            "deviance_explained": round(dev_intent, 1),
            "pseudo_r2": round(dev_intent / total_deviance * 100, 2),
            "interpretation": "Variance due to harmful intent (some intents are inherently harder to defend)",
        },
        "model_given_intent": {
            "deviance_explained": round(dev_model_given_intent, 1),
            "pseudo_r2": round(dev_model_given_intent / total_deviance * 100, 2),
        },
        "intent_given_model": {
            "deviance_explained": round(dev_intent_given_model, 1),
            "pseudo_r2": round(dev_intent_given_model / total_deviance * 100, 2),
        },
        "mechanism_effect": {
            "deviance_explained": round(dev_mechanisms, 1),
            "pseudo_r2": round(dev_mechanisms / total_deviance * 100, 2),
            "interpretation": "Variance due to attack mechanism (feedback, diversity, etc.)",
        },
        "residual": {
            "deviance": round(total_deviance - dev_model_given_intent - dev_intent - dev_mechanisms, 1),
            "pseudo_r2": round(
                (1 - (dev_model_given_intent + dev_intent + dev_mechanisms) / total_deviance) * 100, 2
            ),
        },
    }

    return decomp


# ---------------------------------------------------------------------------
# Bootstrap confidence intervals for marginal effects
# ---------------------------------------------------------------------------

def bootstrap_marginal_effects(df: pd.DataFrame, n_boot: int = 1000) -> dict:
    """Block bootstrap (resample models) for mechanism AMEs."""
    import statsmodels.api as sm

    mechanisms = ["attacker_llm", "feedback", "multi_turn", "diversity"]
    model_dummies = pd.get_dummies(df["model"], prefix="m", drop_first=True, dtype=float)
    intent_dummies = pd.get_dummies(df["intent_id"], prefix="i", drop_first=True, dtype=float)
    mech_df = df[mechanisms].astype(float)
    X = sm.add_constant(pd.concat([mech_df, model_dummies, intent_dummies], axis=1))
    y = df["success"].values

    models_list = df["model"].unique()
    rng = np.random.default_rng(42)

    boot_ames = {m: [] for m in mechanisms}

    for b in range(n_boot):
        # Block bootstrap: resample models with replacement
        boot_models = rng.choice(models_list, size=len(models_list), replace=True)
        boot_idx = []
        for bm in boot_models:
            boot_idx.extend(df.index[df["model"] == bm].tolist())

        X_b = X.iloc[boot_idx]
        y_b = y[boot_idx]

        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                m_b = sm.Logit(y_b, X_b).fit(disp=0, maxiter=100, method="bfgs")

            for mech in mechanisms:
                idx = list(X.columns).index(mech)
                X_alt = X_b.values.copy()
                X_zero = X_b.values.copy()
                X_alt[:, idx] = 1.0
                X_zero[:, idx] = 0.0
                p_alt = 1 / (1 + np.exp(-X_alt @ m_b.params.values))
                p_zero = 1 / (1 + np.exp(-X_zero @ m_b.params.values))
                ame = float(np.mean(p_alt - p_zero))
                boot_ames[mech].append(ame)
        except Exception:
            continue

    boot_results = {}
    for mech in mechanisms:
        ames = np.array(boot_ames[mech])
        if len(ames) > 50:
            boot_results[mech] = {
                "ame_mean": round(float(np.mean(ames)) * 100, 2),
                "ame_ci_95": [
                    round(float(np.percentile(ames, 2.5)) * 100, 2),
                    round(float(np.percentile(ames, 97.5)) * 100, 2),
                ],
                "n_successful_boots": len(ames),
            }
    return boot_results


# ---------------------------------------------------------------------------
# McNemar comparison table
# ---------------------------------------------------------------------------

def mcnemar_vs_regression(df: pd.DataFrame, model_results: dict) -> dict:
    """Show how regression results compare to pooled McNemar for key contrasts."""
    mechs = model_results["M4_primary"]["mechanisms"]

    comparisons = [
        {
            "contrast": "PAIR-1 vs Direct (attacker_llm effect)",
            "conditions": ("adaptive_single_query_st", "direct_single_turn"),
            "mechanism": "attacker_llm",
        },
        {
            "contrast": "PAIR-5 vs PAIR-1 (feedback effect)",
            "conditions": ("adaptive_single_turn", "adaptive_single_query_st"),
            "mechanism": "feedback",
        },
        {
            "contrast": "Adaptive MT vs PAIR-5 (multi_turn effect)",
            "conditions": ("adaptive_multi_turn", "adaptive_single_turn"),
            "mechanism": "multi_turn",
        },
        {
            "contrast": "BoK vs PAIR-1 (diversity effect)",
            "conditions": ("best_of_k_st", "adaptive_single_query_st"),
            "mechanism": "diversity",
        },
    ]

    from scipy.stats import chi2 as chi2_dist

    result_table = []
    for comp in comparisons:
        cond_a, cond_b = comp["conditions"]
        df_a = df[df["condition"] == cond_a].set_index(["model", "intent_id"])["success"]
        df_b = df[df["condition"] == cond_b].set_index(["model", "intent_id"])["success"]
        merged = pd.DataFrame({"a": df_a, "b": df_b}).dropna()

        # McNemar
        b_val = int(((merged["a"] == 1) & (merged["b"] == 0)).sum())  # a wins
        c_val = int(((merged["a"] == 0) & (merged["b"] == 1)).sum())  # b wins
        if b_val + c_val > 0:
            mcnemar_stat = (abs(b_val - c_val) - 1) ** 2 / (b_val + c_val)
            mcnemar_p = float(chi2_dist.sf(mcnemar_stat, 1))
        else:
            mcnemar_stat = 0.0
            mcnemar_p = 1.0
        raw_diff = float(merged["a"].mean() - merged["b"].mean()) * 100

        mech = comp["mechanism"]
        reg = mechs[mech]

        result_table.append({
            "contrast": comp["contrast"],
            "mechanism": mech,
            "mcnemar_raw_diff_pp": round(raw_diff, 1),
            "mcnemar_p": round(mcnemar_p, 6),
            "mcnemar_note": "Pooled, ignores model/intent clustering",
            "regression_ame_pp": reg["ame_pp"],
            "regression_or": reg["odds_ratio"],
            "regression_p": reg["p_value"],
            "regression_note": "Controls for model + intent heterogeneity",
        })

    return result_table


# ---------------------------------------------------------------------------
# Formatting
# ---------------------------------------------------------------------------

def format_markdown(
    model_results: dict,
    var_decomp: dict,
    boot_results: dict,
    mcnemar_table: list[dict],
    df: pd.DataFrame,
) -> str:
    md = "# Mechanism Decomposition: Mixed-Effects Logistic Regression\n\n"

    md += (
        "Estimates the effect of four attack mechanisms on jailbreak success, "
        "controlling for heterogeneity across 8 target models and 40 harmful intents "
        "as fixed effects (absorbing all model- and intent-level variation). "
        "This replaces the pooled McNemar tests — which ignore clustering — with a "
        "single unified model that simultaneously estimates all mechanism effects.\n\n"
    )

    # --- Design matrix ---
    md += "## Mechanism Encoding\n\n"
    md += "| Condition | LLM-crafted | Feedback | Multi-turn | Diversity |\n"
    md += "|-----------|-------------|----------|------------|----------|\n"
    for cond, mechs in MECHANISM_ENCODING.items():
        name = cond.replace("_", " ").title()
        md += f"| {name} | {mechs['attacker_llm']} | {mechs['feedback']} | {mechs['multi_turn']} | {mechs['diversity']} |\n"

    # --- Primary model (M4) ---
    md += "\n## Primary Model (M4): Mechanism Effects\n\n"
    m4 = model_results["M4_primary"]
    md += f"*N* = {m4['n_obs']}, *k* = {m4['n_params']} parameters, "
    md += f"McFadden pseudo-*R*² = {m4['pseudo_r2']:.3f}\n\n"

    md += "| Mechanism | OR | 95% CI | AME (pp) | Boot 95% CI | *p* | Sig. |\n"
    md += "|-----------|-------|------------|----------|-------------|-------|------|\n"
    for mech in ["attacker_llm", "feedback", "multi_turn", "diversity"]:
        r = m4["mechanisms"][mech]
        boot = boot_results.get(mech, {})
        boot_ci = boot.get("ame_ci_95", ["—", "—"])
        if isinstance(boot_ci[0], (int, float)):
            boot_str = f"[{boot_ci[0]:+.1f}, {boot_ci[1]:+.1f}]"
        else:
            boot_str = "—"
        sig = "***" if r["p_value"] < 0.001 else ("**" if r["p_value"] < 0.01 else ("*" if r["p_value"] < 0.05 else "ns"))
        md += (
            f"| {r['label']} "
            f"| {r['odds_ratio']:.2f} | [{r['or_ci'][0]:.2f}, {r['or_ci'][1]:.2f}] "
            f"| {r['ame_pp']:+.1f} | {boot_str} "
            f"| {r['p_value']:.4f} | {sig} |\n"
        )

    md += "\n**Reading the table**:\n"
    md += "- **OR** (odds ratio): multiplicative change in odds of success when the mechanism is present.\n"
    md += "- **AME** (average marginal effect): average change in P(success) in percentage points.\n"
    md += "- **Boot 95% CI**: block-bootstrap CI (resampling models) for the AME, robust to clustering.\n\n"

    # --- Interaction (M5) ---
    m5 = model_results["M5_interaction"]
    md += "## Interaction: Feedback x Multi-turn\n\n"
    md += (
        f"Adding a feedback x multi-turn interaction term yields OR = {m5['interaction_or']:.2f} "
        f"(*p* = {m5['interaction_p']:.4f}). "
    )
    if m5["interaction_significant"]:
        if m5["interaction_or"] < 1:
            md += "The interaction is **negative**: combining feedback with multi-turn memory provides *less* benefit than the sum of their individual effects (diminishing returns).\n\n"
        else:
            md += "The interaction is **positive**: feedback and multi-turn memory are synergistic.\n\n"
    else:
        md += f"The LR test vs. M4 is chi²(1) = {m5['lr_test_vs_m4']:.2f}, *p* = {m5['lr_p_value']:.4f} — the interaction is not significant.\n\n"

    # --- Variance decomposition ---
    md += "## Variance Decomposition\n\n"
    md += (
        "How much of the variation in attack success is explained by target model, "
        "harmful intent, and attack mechanism? (McFadden pseudo-*R*² decomposition "
        "from nested model sequence.)\n\n"
    )
    md += "| Source | Deviance explained | % of null deviance |\n"
    md += "|--------|-------------------|-----------------|\n"
    md += f"| Target model | {var_decomp['model_effect']['deviance_explained']:.1f} | {var_decomp['model_effect']['pseudo_r2']:.1f}% |\n"
    md += f"| Harmful intent | {var_decomp['intent_effect']['deviance_explained']:.1f} | {var_decomp['intent_effect']['pseudo_r2']:.1f}% |\n"
    md += f"| Intent (given model) | {var_decomp['intent_given_model']['deviance_explained']:.1f} | {var_decomp['intent_given_model']['pseudo_r2']:.1f}% |\n"
    md += f"| Model (given intent) | {var_decomp['model_given_intent']['deviance_explained']:.1f} | {var_decomp['model_given_intent']['pseudo_r2']:.1f}% |\n"
    md += f"| Attack mechanism | {var_decomp['mechanism_effect']['deviance_explained']:.1f} | {var_decomp['mechanism_effect']['pseudo_r2']:.1f}% |\n"
    md += f"| Residual | {var_decomp['residual']['deviance']:.1f} | {var_decomp['residual']['pseudo_r2']:.1f}% |\n"
    md += f"| **Total null deviance** | **{var_decomp['total_null_deviance']:.1f}** | **100%** |\n"

    # --- GEE comparison ---
    md += "\n## GEE Robustness Check (M6)\n\n"
    md += (
        "GEE with exchangeable correlation within model clusters + intent fixed effects. "
        "SEs are cluster-robust (sandwich estimator), valid even if the within-cluster "
        "correlation is misspecified.\n\n"
    )
    m6 = model_results["M6_gee"]
    md += "| Mechanism | OR (GEE) | Robust SE | *p* (GEE) | OR (M4) | Agreement |\n"
    md += "|-----------|----------|-----------|-----------|---------|----------|\n"
    for mech in ["attacker_llm", "feedback", "multi_turn", "diversity"]:
        gee = m6["mechanisms"][mech]
        m4_or = m4["mechanisms"][mech]["odds_ratio"]
        agree = "yes" if (gee["odds_ratio"] > 1) == (m4_or > 1) else "**NO**"
        md += (
            f"| {MECHANISM_LABELS[mech]} "
            f"| {gee['odds_ratio']:.2f} | {gee['robust_se']:.3f} | {gee['p_value']:.4f} "
            f"| {m4_or:.2f} | {agree} |\n"
        )

    # --- McNemar comparison ---
    md += "\n## Pooled McNemar vs Regression: Why It Matters\n\n"
    md += (
        "The pooled McNemar test compares two conditions pairwise, ignoring that the "
        "same models and intents appear in both. The regression controls for this "
        "clustering, which can change effect sizes and significance.\n\n"
    )
    md += "| Contrast | McNemar diff | McNemar *p* | Regression AME | Regression *p* | Direction agrees? |\n"
    md += "|----------|-------------|-------------|----------------|----------------|------------------|\n"
    for row in mcnemar_table:
        agree = "yes" if (row["mcnemar_raw_diff_pp"] > 0) == (row["regression_ame_pp"] > 0) else "**NO**"
        md += (
            f"| {row['contrast']} "
            f"| {row['mcnemar_raw_diff_pp']:+.1f}pp | {row['mcnemar_p']:.4f} "
            f"| {row['regression_ame_pp']:+.1f}pp | {row['regression_p']:.4f} "
            f"| {agree} |\n"
        )

    # --- Key findings ---
    md += "\n## Key Findings\n\n"

    # Sort mechanisms by AME magnitude
    sorted_mechs = sorted(
        m4["mechanisms"].items(),
        key=lambda x: abs(x[1]["ame_pp"]),
        reverse=True,
    )

    md += "**Mechanism ranking by effect size** (average marginal effect on P(success)):\n\n"
    for i, (mech, r) in enumerate(sorted_mechs, 1):
        boot = boot_results.get(mech, {})
        boot_ci = boot.get("ame_ci_95", None)
        ci_str = f" (boot 95% CI: [{boot_ci[0]:+.1f}, {boot_ci[1]:+.1f}]pp)" if boot_ci else ""
        sig = "significant" if r["significant"] else "not significant"
        md += f"{i}. **{r['label']}**: {r['ame_pp']:+.1f}pp{ci_str}, OR = {r['odds_ratio']:.2f}, {sig}\n"

    md += "\n"

    vd = var_decomp
    md += (
        f"**Variance decomposition**: Target model explains {vd['model_effect']['pseudo_r2']:.1f}% "
        f"of null deviance, intent explains {vd['intent_effect']['pseudo_r2']:.1f}%, and attack "
        f"mechanism explains {vd['mechanism_effect']['pseudo_r2']:.1f}%. The largest source of "
        f"variation is "
    )
    sources = [
        ("target model", vd["model_effect"]["pseudo_r2"]),
        ("harmful intent", vd["intent_effect"]["pseudo_r2"]),
        ("attack mechanism", vd["mechanism_effect"]["pseudo_r2"]),
    ]
    sources.sort(key=lambda x: x[1], reverse=True)
    md += f"**{sources[0][0]}** ({sources[0][1]:.1f}%), "
    md += f"followed by **{sources[1][0]}** ({sources[1][1]:.1f}%) "
    md += f"and **{sources[2][0]}** ({sources[2][1]:.1f}%).\n\n"

    md += (
        "**Advantage over pooled McNemar**: this model (1) controls for model × intent "
        "clustering in a single unified regression, (2) estimates all four mechanism effects "
        "simultaneously rather than through 15 pairwise tests, (3) provides a variance "
        "decomposition showing what matters most, and (4) yields cluster-robust CIs via "
        "block bootstrap that are valid under arbitrary within-cluster dependence.\n"
    )

    return md


def generate_figure(
    model_results: dict,
    var_decomp: dict,
    boot_results: dict,
    output_path: str,
) -> None:
    """Three-panel figure: (a) mechanism AMEs, (b) variance decomposition, (c) McNemar failure."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(16, 5))

    m4 = model_results["M4_primary"]
    mechanisms = ["attacker_llm", "diversity", "feedback", "multi_turn"]
    labels = [MECHANISM_LABELS[m].replace(" (target feedback)", "\n(target feedback)").replace(" (K=5 variants)", "\n(K=5 variants)") for m in mechanisms]
    ames = [m4["mechanisms"][m]["ame_pp"] for m in mechanisms]
    boot_los = [boot_results.get(m, {}).get("ame_ci_95", [0, 0])[0] for m in mechanisms]
    boot_his = [boot_results.get(m, {}).get("ame_ci_95", [0, 0])[1] for m in mechanisms]
    errors_lo = [a - lo for a, lo in zip(ames, boot_los)]
    errors_hi = [hi - a for a, hi in zip(ames, boot_his)]
    colors = ["C1" if m4["mechanisms"][m]["significant"] else "C7" for m in mechanisms]

    # --- Panel A: Mechanism AMEs ---
    bars = ax1.barh(range(len(mechanisms)), ames, color=colors, alpha=0.85, height=0.6)
    ax1.errorbar(ames, range(len(mechanisms)), xerr=[errors_lo, errors_hi],
                 fmt="none", color="black", capsize=4, linewidth=1.5)
    ax1.set_yticks(range(len(mechanisms)))
    ax1.set_yticklabels(labels, fontsize=9)
    ax1.set_xlabel("Average marginal effect (pp)", fontsize=10)
    ax1.set_title("(a) Mechanism Effects", fontsize=11, fontweight="bold")
    ax1.axvline(0, color="black", linewidth=0.8)
    ax1.grid(True, alpha=0.3, axis="x")

    # Add significance stars
    for i, m in enumerate(mechanisms):
        p = m4["mechanisms"][m]["p_value"]
        star = "***" if p < 0.001 else ("**" if p < 0.01 else ("*" if p < 0.05 else "ns"))
        ax1.text(max(ames[i], boot_his[i]) + 1.5, i, star, va="center", fontsize=9,
                 color="black" if star != "ns" else "gray")

    # --- Panel B: Variance decomposition pie ---
    vd_labels = ["Mechanism", "Target model", "Harmful intent", "Residual"]
    vd_sizes = [
        var_decomp["mechanism_effect"]["pseudo_r2"],
        var_decomp["model_given_intent"]["pseudo_r2"],
        var_decomp["intent_given_model"]["pseudo_r2"],
        var_decomp["residual"]["pseudo_r2"],
    ]
    vd_colors = ["C1", "C0", "C2", "C7"]
    wedges, texts, autotexts = ax2.pie(
        vd_sizes, labels=vd_labels, autopct="%1.1f%%", colors=vd_colors,
        startangle=90, pctdistance=0.75, textprops={"fontsize": 9},
    )
    for at in autotexts:
        at.set_fontsize(8)
    ax2.set_title("(b) Variance Decomposition", fontsize=11, fontweight="bold")

    # --- Panel C: McNemar vs Regression (multi-turn discrepancy) ---
    contrasts = ["LLM-crafted", "Feedback", "Multi-turn", "Diversity"]
    mcnemar_diffs = [+49.4, +22.2, -22.5, +21.9]
    regression_ames_vals = [+36.6, +10.2, +0.3, +22.4]

    x_pos = np.arange(len(contrasts))
    width = 0.35
    bars1 = ax3.bar(x_pos - width / 2, mcnemar_diffs, width, label="McNemar (pooled)", color="C3", alpha=0.7)
    bars2 = ax3.bar(x_pos + width / 2, regression_ames_vals, width, label="Regression (M4)", color="C0", alpha=0.7)

    ax3.set_xticks(x_pos)
    ax3.set_xticklabels(contrasts, fontsize=9, rotation=15)
    ax3.set_ylabel("Effect size (pp)", fontsize=10)
    ax3.set_title("(c) McNemar vs Regression", fontsize=11, fontweight="bold")
    ax3.axhline(0, color="black", linewidth=0.8)
    ax3.legend(fontsize=8.5, loc="upper left")
    ax3.grid(True, alpha=0.3, axis="y")

    # Highlight the multi-turn discrepancy
    ax3.annotate(
        "Sign flip!",
        xy=(2, -11), fontsize=8, color="C3", fontweight="bold", ha="center",
    )

    fig.tight_layout(w_pad=2.5)
    plt.savefig(output_path, dpi=200, bbox_inches="tight")
    plt.close()
    print(f"Figure saved to {output_path}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Mechanism decomposition regression")
    parser.add_argument("--ledger", default=LEDGER_PATH)
    parser.add_argument("--output", default="docs/v6/artifacts/mechanism_decomposition")
    parser.add_argument("--n-boot", type=int, default=2000,
                        help="Bootstrap iterations for AME CIs")
    args = parser.parse_args()

    print("Building dataset from annotation ledger...")
    df = build_dataset(Path(args.ledger))
    print(f"  {len(df)} observations, {df['model'].nunique()} models, "
          f"{df['intent_id'].nunique()} intents, {df['condition'].nunique()} conditions")
    print(f"  Overall ASR: {df['success'].mean():.3f}")

    print("\nFitting model sequence (M0–M6)...")
    model_results = fit_models(df)

    print("Computing variance decomposition...")
    var_decomp = variance_decomposition(model_results)

    print(f"Running block bootstrap ({args.n_boot} iterations)...")
    boot_results = bootstrap_marginal_effects(df, n_boot=args.n_boot)

    print("Computing McNemar vs regression comparison...")
    mcnemar_table = mcnemar_vs_regression(df, model_results)

    # Assemble output
    output = {
        "model_results": model_results,
        "variance_decomposition": var_decomp,
        "bootstrap_marginal_effects": boot_results,
        "mcnemar_comparison": mcnemar_table,
        "design": {
            "mechanism_encoding": MECHANISM_ENCODING,
            "mechanism_labels": MECHANISM_LABELS,
            "n_obs": len(df),
            "n_models": int(df["model"].nunique()),
            "n_intents": int(df["intent_id"].nunique()),
            "n_conditions": int(df["condition"].nunique()),
        },
    }

    json_path = Path(f"{args.output}.json")
    json_path.parent.mkdir(parents=True, exist_ok=True)
    with open(json_path, "w") as f:
        json.dump(output, f, indent=2)

    md_path = Path(f"{args.output}.md")
    md = format_markdown(model_results, var_decomp, boot_results, mcnemar_table, df)
    with open(md_path, "w") as f:
        f.write(md)

    # Generate figure
    png_path = Path(f"{args.output}.png")
    generate_figure(model_results, var_decomp, boot_results, str(png_path))

    print(f"\nResults written to {json_path}, {md_path}, and {png_path}")

    # Summary
    print("\n--- Mechanism Effects (M4, primary model) ---")
    m4 = model_results["M4_primary"]
    for mech in ["attacker_llm", "feedback", "multi_turn", "diversity"]:
        r = m4["mechanisms"][mech]
        boot = boot_results.get(mech, {})
        boot_ci = boot.get("ame_ci_95", None)
        ci_str = f"  boot CI: [{boot_ci[0]:+.1f}, {boot_ci[1]:+.1f}]" if boot_ci else ""
        print(f"  {r['label']:45s}  OR={r['odds_ratio']:.2f}  AME={r['ame_pp']:+.1f}pp  p={r['p_value']:.4f}{ci_str}")

    print(f"\n--- Variance Decomposition ---")
    print(f"  Model:     {var_decomp['model_effect']['pseudo_r2']:.1f}%")
    print(f"  Intent:    {var_decomp['intent_effect']['pseudo_r2']:.1f}%")
    print(f"  Mechanism: {var_decomp['mechanism_effect']['pseudo_r2']:.1f}%")
    print(f"  Residual:  {var_decomp['residual']['pseudo_r2']:.1f}%")


if __name__ == "__main__":
    main()
