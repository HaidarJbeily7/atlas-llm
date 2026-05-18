# Mechanism Decomposition: Mixed-Effects Logistic Regression

Estimates the effect of four attack mechanisms on jailbreak success, controlling for heterogeneity across 8 target models and 40 harmful intents as fixed effects (absorbing all model- and intent-level variation). This replaces the pooled McNemar tests — which ignore clustering — with a single unified model that simultaneously estimates all mechanism effects.

## Mechanism Encoding

| Condition | LLM-crafted | Feedback | Multi-turn | Diversity |
|-----------|-------------|----------|------------|----------|
| Direct Single Turn | 0 | 0 | 0 | 0 |
| Scripted Multi Turn | 0 | 0 | 1 | 0 |
| Adaptive Single Query St | 1 | 0 | 0 | 0 |
| Adaptive Single Turn | 1 | 1 | 0 | 0 |
| Adaptive Multi Turn | 1 | 1 | 1 | 0 |
| Best Of K St | 1 | 0 | 0 | 1 |

## Primary Model (M4): Mechanism Effects

*N* = 1920, *k* = 51 parameters, McFadden pseudo-*R*² = 0.344

| Mechanism | OR | 95% CI | AME (pp) | Boot 95% CI | *p* | Sig. |
|-----------|-------|------------|----------|-------------|-------|------|
| LLM-crafted prompt | 8.30 | [5.73, 12.04] | +36.6 | [+28.2, +44.1] | 0.0000 | *** |
| Iterative refinement (target feedback) | 1.98 | [1.37, 2.84] | +10.2 | [+3.0, +17.4] | 0.0003 | *** |
| Multi-turn memory | 1.02 | [0.77, 1.36] | +0.3 | [-6.0, +7.5] | 0.8847 | ns |
| Static diversity (K=5 variants) | 4.99 | [3.19, 7.81] | +22.4 | [+16.9, +27.8] | 0.0000 | *** |

**Reading the table**:
- **OR** (odds ratio): multiplicative change in odds of success when the mechanism is present.
- **AME** (average marginal effect): average change in P(success) in percentage points.
- **Boot 95% CI**: block-bootstrap CI (resampling models) for the AME, robust to clustering.

## Interaction: Feedback x Multi-turn

Adding a feedback x multi-turn interaction term yields OR = 0.04 (*p* = 0.0000). The interaction is **negative**: combining feedback with multi-turn memory provides *less* benefit than the sum of their individual effects (diminishing returns).

## Variance Decomposition

How much of the variation in attack success is explained by target model, harmful intent, and attack mechanism? (McFadden pseudo-*R*² decomposition from nested model sequence.)

| Source | Deviance explained | % of null deviance |
|--------|-------------------|-----------------|
| Target model | 129.7 | 5.0% |
| Harmful intent | 174.5 | 6.7% |
| Intent (given model) | 187.6 | 7.2% |
| Model (given intent) | 142.8 | 5.5% |
| Attack mechanism | 579.3 | 22.2% |
| Residual | 1710.2 | 65.6% |
| **Total null deviance** | **2606.7** | **100%** |

## GEE Robustness Check (M6)

GEE with exchangeable correlation within model clusters + intent fixed effects. SEs are cluster-robust (sandwich estimator), valid even if the within-cluster correlation is misspecified.

| Mechanism | OR (GEE) | Robust SE | *p* (GEE) | OR (M4) | Agreement |
|-----------|----------|-----------|-----------|---------|----------|
| LLM-crafted prompt | 6.50 | 0.266 | 0.0000 | 8.30 | yes |
| Iterative refinement (target feedback) | 1.83 | 0.209 | 0.0039 | 1.98 | yes |
| Multi-turn memory | 1.02 | 0.210 | 0.9292 | 1.02 | yes |
| Static diversity (K=5 variants) | 4.21 | 0.297 | 0.0000 | 4.99 | yes |

## Pooled McNemar vs Regression: Why It Matters

The pooled McNemar test compares two conditions pairwise, ignoring that the same models and intents appear in both. The regression controls for this clustering, which can change effect sizes and significance.

| Contrast | McNemar diff | McNemar *p* | Regression AME | Regression *p* | Direction agrees? |
|----------|-------------|-------------|----------------|----------------|------------------|
| PAIR-1 vs Direct (attacker_llm effect) | +49.4pp | 0.0000 | +36.6pp | 0.0000 | yes |
| PAIR-5 vs PAIR-1 (feedback effect) | +22.2pp | 0.0000 | +10.2pp | 0.0003 | yes |
| Adaptive MT vs PAIR-5 (multi_turn effect) | -22.5pp | 0.0000 | +0.3pp | 0.8847 | **NO** |
| BoK vs PAIR-1 (diversity effect) | +21.9pp | 0.0000 | +22.4pp | 0.0000 | yes |

## Key Findings

**Mechanism ranking by effect size** (average marginal effect on P(success)):

1. **LLM-crafted prompt**: +36.6pp (boot 95% CI: [+28.2, +44.1]pp), OR = 8.30, significant
2. **Static diversity (K=5 variants)**: +22.4pp (boot 95% CI: [+16.9, +27.8]pp), OR = 4.99, significant
3. **Iterative refinement (target feedback)**: +10.2pp (boot 95% CI: [+3.0, +17.4]pp), OR = 1.98, significant
4. **Multi-turn memory**: +0.3pp (boot 95% CI: [-6.0, +7.5]pp), OR = 1.02, not significant

**Variance decomposition**: Target model explains 5.0% of null deviance, intent explains 6.7%, and attack mechanism explains 22.2%. The largest source of variation is **attack mechanism** (22.2%), followed by **harmful intent** (6.7%) and **target model** (5.0%).

**Advantage over pooled McNemar**: this model (1) controls for model × intent clustering in a single unified regression, (2) estimates all four mechanism effects simultaneously rather than through 15 pairwise tests, (3) provides a variance decomposition showing what matters most, and (4) yields cluster-robust CIs via block bootstrap that are valid under arbitrary within-cluster dependence.
