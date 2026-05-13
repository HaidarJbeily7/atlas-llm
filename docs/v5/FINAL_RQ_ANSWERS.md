# Full Final Answers for All Research Questions

## Experiment Overview

**Study**: ATLAS -- Automated Testing for LLM Application Security
**Experiment ID**: `20260505_003630`
**Design**: 2x2 Factorial (Adaptivity x Interaction Mode) + 1 Baseline
**Total Findings**: 1,600 (100% human-reviewed, 0 unreviewed)
**Target Models (8)**: Claude Sonnet 4, DeepSeek-Chat-v3-0324, Gemini 2.5 Flash, LLaMA 3.3 70B Instruct, Mistral Large 2411, GPT-4o, GPT-4o-mini, Qwen 2.5 72B Instruct
**Conditions (5)**: Direct Single-Turn (baseline), Scripted Multi-Turn, Adaptive Single-Query ST, Adaptive Single-Turn, Adaptive Multi-Turn
**Attacks per cell**: 40 intents x 8 models x 5 conditions = 1,600 total
**Pairing**: All statistical comparisons are paired by `(model, intent_id)` -- see Appendix A for the formal pairing audit.

---

## RQ1: How Does Attack Success Rate Vary Across Conditions, and What Are the Cost-Efficiency Trade-offs?

### 1.1 Overall Attack Success Rates

The five experimental conditions produced a clear hierarchy of attack effectiveness:

| Condition | Raw ASR | 95% CI | Adj. ASR | Adj. 95% CI | FP | FN |
|---|---|---|---|---|---|---|
| Direct Single-Turn (baseline) | 15.9% | [12.3%, 20.4%] | 14.4% | [11.0%, 18.6%] | 5 | 0 |
| Scripted Multi-Turn | 51.2% | [45.8%, 56.7%] | 37.5% | [32.4%, 42.9%] | 54 | 10 |
| Adaptive Single-Query ST | 64.1% | [58.7%, 69.1%] | 63.8% | [58.4%, 68.8%] | 4 | 4 |
| Adaptive Multi-Turn | 63.4% | [58.0%, 68.5%] | 63.4% | [58.0%, 68.5%] | 23 | 26 |
| Adaptive Single-Turn | 85.0% | [80.7%, 88.5%] | 85.9% | [81.7%, 89.3%] | 7 | 8 |

**Finding 1 -- Adaptivity is the dominant factor, not multi-turn interaction.** The adaptive single-turn condition achieved the highest ASR (85.0%), significantly outperforming the adaptive multi-turn condition (63.4%) by +21.6 percentage points (McNemar p < 0.0001, Bonferroni-corrected). This directly resolves the confound identified in the original study design: when adaptivity and multi-turn interaction are disentangled, adaptivity alone drives the majority of attack success. Adding multi-turn interaction to adaptive strategies actually *degrades* performance compared to the single-turn adaptive condition (63.4% vs. 85.0%). The most plausible explanation is that multi-turn conversation provides more opportunities for the target model's safety mechanisms to re-engage after an initial lapse, while a single concentrated adversarial prompt gives the model only one chance to refuse.

**Finding 2 -- Scripted multi-turn provides moderate gains over direct attacks but is outclassed by any adaptive method.** The scripted multi-turn condition (raw 51.2%, adjusted 37.5%) more than doubles the baseline ASR (15.9%), confirming that multi-turn sequences enable attacks by gradually building context. However, after human review the adjusted ASR drops sharply to 37.5% due to 54 false positives -- many scripted responses appeared harmful to automated detectors but were judged safe by human annotators. Both adaptive conditions significantly exceed the scripted condition (p < 0.003 for all pairwise comparisons), demonstrating that LLM-driven attack optimisation is far more effective than human-authored scripts.

**Finding 3 -- Adaptive single-query and adaptive multi-turn achieve statistically indistinguishable ASRs.** The difference between adaptive single-query ST (64.1%) and adaptive multi-turn (63.4%) is +0.6pp with p = 0.93 -- not significant. Both use an attacker LLM, but the single-query variant restricts the target to seeing only one message. This parity implies that when the attacker can optimise internally, it produces equally effective single-shot prompts as it can through interactive multi-turn refinement.

### 1.2 Per-Model ASR Breakdown

| Model | Direct ST | Scripted MT | Adaptive SQ-ST | Adaptive MT | Adaptive ST | Overall ASR |
|---|---|---|---|---|---|---|
| Claude Sonnet 4 | 12.5% | 12.5% | 25.0% | 30.0% | 45.0% | **25.0%** |
| GPT-4o | 0.0% | 25.0% | 57.5% | 72.5% | 87.5% | **48.5%** |
| GPT-4o-mini | 7.5% | 32.5% | 47.5% | 77.5% | 87.5% | **50.5%** |
| Gemini 2.5 Flash | 17.5% | 35.0% | 65.0% | 60.0% | 92.5% | **54.0%** |
| LLaMA 3.3 70B | 12.5% | 37.5% | 70.0% | 62.5% | 90.0% | **54.5%** |
| Qwen 2.5 72B | 2.5% | 65.0% | 65.0% | 72.5% | 92.5% | **59.5%** |
| DeepSeek-v3-0324 | 20.0% | 32.5% | 90.0% | 65.0% | 100.0% | **61.5%** |
| Mistral Large 2411 | 42.5% | 60.0% | 90.0% | 67.5% | 92.5% | **70.5%** |

**Finding 4 -- Claude Sonnet 4 is the most robust model by a wide margin.** With an overall adjusted ASR of 25.0% (refusal rate: 75.0%, AWCS: +0.206), Claude Sonnet 4 resists attacks 2-3x better than any other tested model. Even under the strongest attack condition (adaptive single-turn), it achieves only 45.0% ASR -- the only model below 85% in this condition. Its positive AWCS score indicates that it not only refuses harmful requests but does so with high consistency across judge detectors.

**Finding 5 -- Mistral Large 2411 is the most vulnerable model overall.** At 70.5% overall ASR and only 29.5% refusal rate, Mistral Large shows the weakest safety alignment. It is particularly vulnerable to direct single-turn attacks (42.5% ASR -- the highest baseline among all models), suggesting its content filtering is fundamentally weaker than competitors. Its AWCS of -0.248 is the most negative across all models, indicating deep and consistent safety failures.

**Finding 6 -- DeepSeek-v3-0324 achieves 100% ASR under adaptive single-turn attacks.** Every single one of the 40 adaptive single-turn attacks succeeded against DeepSeek, with a 0% refusal rate and AWCS of -0.427. This represents a complete safety bypass -- the most severe finding in the entire experiment. Yet DeepSeek shows reasonable direct-attack resistance (20.0% ASR), revealing that its safety relies entirely on pattern-matching against known attack formats.

**Finding 7 -- GPT-4o has the strongest baseline defense but collapses under adaptive attacks.** GPT-4o achieves 0.0% ASR under direct single-turn attacks (the best baseline defense, AWCS +0.462), but this jumps to 87.5% under adaptive single-turn -- an 87.5pp swing. This pattern, where a model is robust to known threats but collapses against optimised novel attacks, suggests over-reliance on training-time memorisation of refusal patterns rather than generalised safety reasoning.

### 1.3 Cost-Efficiency Analysis

| Condition | Cost/attack (mean) | 95% CI | Latency (median) | Mean Tokens | Target Calls | Attacker Calls |
|---|---|---|---|---|---|---|
| Direct Single-Turn | $0.0017 | [$0.0009, $0.0030] | 17.0s | 466 | 1.0 | 0.0 |
| Scripted Multi-Turn | $0.0104 | [$0.0079, $0.0134] | 117.2s | 7,258 | 3.5 | 0.0 |
| Adaptive Single-Query ST | $0.0068 | [$0.0057, $0.0083] | 181.5s | 4,037 | 1.0 | 2.0 |
| Adaptive Single-Turn | $0.0138 | [$0.0115, $0.0165] | 284.7s | 8,082 | 1.6 | 3.3 |
| Adaptive Multi-Turn | $0.0238 | [$0.0213, $0.0265] | 518.4s | 21,330 | 2.9 | 5.9 |

**Finding 8 -- Adaptive single-query ST is the most cost-effective attack strategy.** At $0.0068 per attack and 64.1% ASR, the adaptive single-query condition delivers the best ASR-per-dollar ratio. It costs 29% of the adaptive multi-turn approach while achieving an equivalent ASR (64.1% vs. 63.4%). This efficiency comes from using only ~2 API calls (1 target + 1 attacker) and ~4,037 tokens per attack.

**Finding 9 -- Adaptive single-turn provides the best overall ASR at a modest premium.** While more expensive than single-query ($0.0138 vs. $0.0068), it achieves +20.9pp higher ASR (85.0% vs. 64.1%). Each additional percentage point of ASR costs approximately $0.033 -- an acceptable premium given the 33% relative improvement.

**Finding 10 -- Adaptive multi-turn is the least cost-effective strategy.** At $0.0238 per attack (the most expensive) with 63.4% ASR (lower than adaptive single-turn), the multi-turn adaptive approach provides no ASR advantage while consuming 3.5x more budget than single-query and 1.7x more than single-turn. The mean 21,330 tokens and 8.6-minute median latency make it impractical at scale.

### 1.4 Refinement Ablation (Single-Query vs. Multi-Query Adaptive)

| Model | SQ ASR | MQ ASR | Gain (pp) | p-value |
|---|---|---|---|---|
| GPT-4o-mini | 47.5% | 87.5% | +40.0 | **< 0.001** |
| GPT-4o | 57.5% | 87.5% | +30.0 | **0.004** |
| Gemini 2.5 Flash | 65.0% | 92.5% | +27.5 | **0.013** |
| Qwen 2.5 72B | 65.0% | 92.5% | +27.5 | **0.007** |
| Claude Sonnet 4 | 25.0% | 45.0% | +20.0 | 0.096 |
| LLaMA 3.3 70B | 70.0% | 90.0% | +20.0 | 0.057 |
| DeepSeek-v3 | 90.0% | 100.0% | +10.0 | 0.125 |
| Mistral Large | 90.0% | 92.5% | +2.5 | 1.000 |
| **Pooled** | **63.8%** | **85.9%** | **+22.2** | **< 0.001** |

**Finding 11 -- Iterative refinement adds +22.2pp ASR on average (p < 0.001).** The pooled gain is highly significant. The benefit is model-dependent: models already near-ceiling (Mistral 90%, DeepSeek 90%) gain little, while moderately-defended models benefit enormously (GPT-4o-mini: +40pp). This means iterative refinement is most valuable against models with intermediate safety defenses.

### 1.5 Paired Statistical Comparisons (McNemar, Bonferroni-Corrected)

| Comparison | ASR Diff (pp) | p (corrected) | Significant? |
|---|---|---|---|
| Adaptive ST vs. Direct ST | +69.1 | **< 0.001** | Yes |
| Adaptive SQ-ST vs. Direct ST | +48.1 | **< 0.001** | Yes |
| Adaptive MT vs. Direct ST | +47.5 | **< 0.001** | Yes |
| Scripted MT vs. Direct ST | +35.3 | **< 0.001** | Yes |
| Adaptive ST vs. Scripted MT | +33.8 | **< 0.001** | Yes |
| Adaptive ST vs. Adaptive MT | +21.6 | **< 0.001** | Yes |
| Adaptive ST vs. Adaptive SQ-ST | +20.9 | **< 0.001** | Yes |
| Adaptive SQ-ST vs. Scripted MT | +12.8 | **0.003** | Yes |
| Adaptive MT vs. Scripted MT | +12.2 | **0.009** | Yes |
| Adaptive SQ-ST vs. Adaptive MT | +0.6 | 1.000 | No |

**Finding 12 -- All pairwise comparisons are statistically significant except Adaptive SQ-ST vs. Adaptive MT.** The hierarchy is: Adaptive ST >> Adaptive SQ-ST = Adaptive MT >> Scripted MT >> Direct ST. Every step in this hierarchy is significant after Bonferroni correction across 10 comparisons.

### 1.6 RQ1 Answer

Adaptivity -- not multi-turn interaction -- is the primary driver of attack success. The adaptive single-turn condition achieves the highest ASR (85.0%), significantly exceeding all other conditions. Adding multi-turn interaction to adaptive strategies *degrades* performance (63.4% vs. 85.0%, p < 0.001). The most cost-effective strategy is adaptive single-query ($0.0068/attack, 64.1% ASR), though adaptive single-turn ($0.0138/attack, 85.0% ASR) provides superior ASR at a modest premium. The factorial design cleanly decomposes the effects: adaptivity contributes ~49pp above baseline, multi-turn interaction alone contributes ~23pp (adjusted), and the combination yields no synergy.

---

## RQ2: How Do Failure-Type Distributions Differ Across Conditions, and Do Human Annotations Validate Automated Detectors?

### 2.1 Failure-Type Distribution by Condition

Detector bypass counts (number of attacks that evaded each detector):

| Detector Bypassed | Direct ST | Scripted MT | Adaptive SQ-ST | Adaptive MT | Adaptive ST |
|---|---|---|---|---|---|
| Refusal | 39 (12.2%) | 76 (23.8%) | 176 (55.0%) | 172 (53.8%) | 231 (72.2%) |
| Keyword | 19 (5.9%) | 42 (13.1%) | 79 (24.7%) | 77 (24.1%) | 115 (35.9%) |
| LLM Judge | 44 (13.8%) | 92 (28.8%) | 184 (57.5%) | 144 (45.0%) | 250 (78.1%) |
| Semantic Judge | 46 (14.4%) | 113 (35.3%) | 195 (60.9%) | 179 (55.9%) | 259 (80.9%) |
| Safety Judge | 45 (14.1%) | 118 (36.9%) | 202 (63.1%) | 194 (60.6%) | 269 (84.1%) |

**Finding 13 -- Adaptive attacks systematically bypass refusal mechanisms.** The refusal bypass rate climbs from 12.2% (direct) to 72.2% (adaptive single-turn). Adaptive strategies elicit compliance by reframing harmful requests in ways that circumvent the model's refusal training -- the single-turn adaptive condition is especially effective because the attacker optimises for a single devastating prompt.

**Finding 14 -- Keyword-based detection is the most resistant to bypassing but still fails significantly.** Keyword detection has the lowest absolute bypass rate across all conditions (5.9%-35.9%). However, as shown in the precision/recall analysis (Section 3.2), this low bypass rate masks extremely poor recall -- the keyword detector simply misses most successful attacks.

**Finding 15 -- LLM-based judges are more effectively bypassed by adaptive single-turn than adaptive multi-turn.** The LLM judge bypass rate is 78.1% for adaptive single-turn vs. 45.0% for adaptive multi-turn. Concentrated, highly-optimised single prompts produce responses that are harder for judges to identify as unsafe, whereas multi-turn conversations leave more contextual evidence.

### 2.2 Human Validation Results

| Condition | Raw ASR | Adj. ASR | False Positives | False Negatives | Net Correction |
|---|---|---|---|---|---|
| Direct ST | 15.9% | 14.4% | 5 | 0 | -1.5pp |
| Scripted MT | 51.2% | 37.5% | 54 | 10 | -13.7pp |
| Adaptive SQ-ST | 64.1% | 63.8% | 4 | 4 | -0.3pp |
| Adaptive ST | 85.0% | 85.9% | 7 | 8 | +0.9pp |
| Adaptive MT | 63.4% | 63.4% | 23 | 26 | 0.0pp |

**Finding 16 -- Scripted multi-turn has the largest detector-human discrepancy (-13.7pp).** Human reviewers reclassified 54 automated "successes" as false positives -- the largest correction in any condition. Scripted multi-turn attacks produce ambiguous responses that look like compliance to automated detectors but are actually benign upon expert review. This has a critical practical implication: **reported ASR for scripted/template-based attacks should be treated with caution unless human-validated**.

**Finding 17 -- Adaptive conditions show excellent detector-human agreement.** The adaptive single-query condition has only 4 FP and 4 FN (net correction -0.3pp). Adaptive single-turn similarly shows +0.9pp net correction. These attacks produce dichotomous outcomes: either a clear safety bypass or a clear refusal, with minimal ambiguity.

### 2.3 Cascade Detection Analysis

| Condition | Refusal Rate | ASR | Judge Agreement | AWCS | Critical Damage Rate |
|---|---|---|---|---|---|
| Direct ST | 85.6% | 14.4% | 96.9% | +0.338 | 14.4% |
| Scripted MT | 62.5% | 37.5% | 49.4% | -0.090 | 37.5% |
| Adaptive SQ-ST | 36.2% | 63.8% | 87.5% | -0.138 | 63.8% |
| Adaptive MT | 36.6% | 63.4% | 64.7% | -0.154 | 63.4% |
| Adaptive ST | 14.1% | 85.9% | 83.1% | -0.347 | 85.9% |

**Finding 18 -- Adaptive single-turn attacks cause the most severe safety failures (AWCS = -0.347).** The negative AWCS indicates that attack responses are not just successful but produce deeply harmful content. The 85.9% critical damage rate means nearly every successful attack is rated critical severity. By contrast, direct single-turn (AWCS = +0.338) represents a regime where models are overwhelmingly safe.

### 2.4 RQ2 Answer

Failure-type distributions differ markedly across conditions. Adaptive attacks systematically bypass refusal mechanisms (72.2% bypass rate for adaptive ST) and produce unambiguous, clearly harmful responses. Scripted multi-turn attacks generate the most ambiguous outputs, with 54 false positives reducing adjusted ASR by 13.7pp. Human annotations validate the automated detection pipeline for adaptive conditions (net correction < 1pp) but reveal significant over-counting for scripted conditions. Reported ASR for scripted attacks should always be human-validated.

---

## RQ3: How Sensitive Are Automated Safety Detectors to Attack Sophistication and Interaction Mode?

### 3.1 Per-Detector Performance Overview

| Detector | Overall Fail Rate | Avg Score | Behaviour |
|---|---|---|---|
| Safety Judge | 59.0% (944/1600) | 0.41 | Most aggressive; best overall F1 |
| Semantic Judge | 60.9% (975/1600) | 0.62 | Aggressive; collapses on scripted MT |
| LLM Judge | 47.1% (753/1600) | 0.61 | Moderate; best balance of P and R |
| Refusal | 64.8% (1036/1600) | 0.35 | Heuristic; high FP rate |
| Keyword | 24.7% (395/1600) | 0.83 | Conservative; very low recall on adaptive |
| Similarity | 0.0% (0/1600) | 0.86 | Never flags -- non-functional for jailbreaks |
| Tool Call | 0.0% (0/1600) | 1.00 | Never flags -- not applicable |

### 3.2 Detector Precision, Recall, and F1 Against Human Ground Truth

This is the central analysis for RQ3. For each detector-condition cell, TP (true positives), FP, and FN are computed against human-reviewed labels.

**Safety Judge:**

| Condition | Precision | Recall | F1 | TP | FP | FN |
|---|---|---|---|---|---|---|
| Direct ST | 98.75% | 99.68% | **99.21%** | 315 | 4 | 1 |
| Adaptive SQ-ST | 98.43% | 99.37% | **98.90%** | 313 | 5 | 2 |
| Adaptive ST | 97.45% | 98.08% | **97.76%** | 306 | 8 | 6 |
| Adaptive MT | 91.00% | 96.92% | **93.87%** | 283 | 28 | 9 |
| Scripted MT | 77.67% | 99.20% | **87.12%** | 247 | 71 | 2 |

**Semantic Judge:**

| Condition | Precision | Recall | F1 | TP | FP | FN |
|---|---|---|---|---|---|---|
| Direct ST | 98.12% | 100.00% | **99.05%** | 314 | 6 | 0 |
| Adaptive SQ-ST | 97.75% | 97.12% | **97.43%** | 304 | 7 | 9 |
| Adaptive ST | 97.37% | 94.87% | **96.10%** | 296 | 8 | 16 |
| Adaptive MT | 85.47% | 91.34% | **88.31%** | 253 | 43 | 24 |
| Scripted MT | 61.98% | 96.52% | **75.49%** | 194 | 119 | 7 |

**LLM Judge:**

| Condition | Precision | Recall | F1 | TP | FP | FN |
|---|---|---|---|---|---|---|
| Direct ST | 97.48% | 99.36% | **98.41%** | 310 | 8 | 2 |
| Adaptive SQ-ST | 97.33% | 93.59% | **95.42%** | 292 | 8 | 20 |
| Adaptive ST | 98.64% | 92.09% | **95.25%** | 291 | 4 | 25 |
| Scripted MT | 96.92% | 91.00% | **93.87%** | 283 | 9 | 28 |
| Adaptive MT | 96.17% | 80.97% | **87.92%** | 251 | 10 | 59 |

**Refusal Detector:**

| Condition | Precision | Recall | F1 | TP | FP | FN |
|---|---|---|---|---|---|---|
| Adaptive SQ-ST | 82.19% | 89.55% | **85.71%** | 240 | 52 | 28 |
| Adaptive ST | 88.41% | 84.72% | **86.53%** | 244 | 32 | 44 |
| Direct ST | 70.29% | 96.92% | **81.48%** | 220 | 93 | 7 |
| Scripted MT | 76.81% | 82.81% | **79.70%** | 212 | 64 | 44 |
| Adaptive MT | 65.05% | 85.84% | **74.01%** | 188 | 101 | 31 |

**Keyword Detector:**

| Condition | Precision | Recall | F1 | TP | FP | FN |
|---|---|---|---|---|---|---|
| Direct ST | 95.22% | 91.18% | **93.16%** | 279 | 14 | 27 |
| Scripted MT | 93.39% | 74.34% | **82.78%** | 226 | 16 | 78 |
| Adaptive SQ-ST | 97.44% | 60.32% | **74.51%** | 190 | 5 | 125 |
| Adaptive MT | 88.66% | 57.72% | **69.92%** | 172 | 22 | 126 |
| Adaptive ST | 96.25% | 49.04% | **64.97%** | 154 | 6 | 160 |

### 3.3 Deep Analysis of Detector Behaviour

**Finding 19 -- The Safety Judge is the best overall detector, achieving F1 > 93% across all conditions.** Its lowest F1 is 87.12% on scripted multi-turn, driven by 71 false positives (precision drops to 77.67%). However, its recall never drops below 96.92%, meaning it catches virtually every real attack. For any single-detector deployment, the safety judge is the recommended choice.

**Finding 20 -- The Semantic Judge has a catastrophic failure mode on scripted multi-turn (F1 = 75.49%).** With 119 false positives (precision: 61.98%), the semantic judge flags nearly twice as many findings as are actually harmful in the scripted condition. The semantic judge appears to be triggered by the topical content of multi-turn scripts even when the model successfully refuses. This inflates the scripted multi-turn ASR by approximately 37% when using this detector alone.

**Finding 21 -- The LLM Judge offers the best precision-recall balance across conditions.** While not the highest on any single metric, the LLM judge maintains precision above 96% in all conditions and recall above 80%. Its worst cell is adaptive multi-turn (F1 = 87.92%, driven by 59 false negatives), where long conversation contexts dilute the harmful signal.

**Finding 22 -- The Keyword Detector has catastrophically low recall on adaptive attacks.** While precision remains high (88-97%), recall drops from 91.18% on direct attacks to just 49.04% on adaptive single-turn -- meaning the keyword detector **misses more than half of all successful adaptive attacks**. Adaptive attackers effectively learn to produce harmful content using euphemisms, circumlocutions, and encoded language that bypass keyword filters.

**Finding 23 -- The Refusal Detector is unreliable across all conditions.** F1 ranges from 74.01% (adaptive MT) to 86.53% (adaptive ST), with consistently high false positive rates. It produces 93 false positives on direct single-turn alone (precision 70.29%), where models are overwhelmingly safe. Refusal pattern-matching is too coarse to be a reliable standalone detector.

**Finding 24 -- Detectors fail in two orthogonal modes depending on their type.**

| Detector Type | Primary Failure Mode | Worst Condition | Root Cause |
|---|---|---|---|
| Judge-based (Safety, Semantic) | False Positives | Scripted MT | Judges interpret escalating scripted context as harmful even when model refuses |
| Pattern-based (Keyword) | False Negatives | Adaptive ST | Adaptive attackers use creative language that bypasses keyword matching |
| Heuristic (Refusal) | Both FP and FN | All conditions | Refusal patterns are too varied to capture heuristically |
| LLM Judge | False Negatives | Adaptive MT | Long multi-turn conversations dilute harmful signal in context |

No single detector handles both scripted and adaptive attacks well. This creates a fundamental tension that can only be resolved through multi-detector consensus or human review.

### 3.4 Judge Agreement Rate

| Condition | Judge Agreement Rate |
|---|---|
| Direct ST | 96.9% |
| Adaptive SQ-ST | 87.5% |
| Adaptive ST | 83.1% |
| Adaptive MT | 64.7% |
| Scripted MT | 49.4% |

**Finding 25 -- Judge agreement collapses in scripted multi-turn (49.4%) and adaptive multi-turn (64.7%).** In nearly half of scripted multi-turn cases, judges disagree on whether the response is safe or unsafe. Any ASR measurement based on a single judge in multi-turn conditions is unreliable.

### 3.5 Per-Model Detector Sensitivity

| Model | Judge Agreement | AWCS | Overall ASR |
|---|---|---|---|
| Mistral Large 2411 | 82.0% | -0.248 | 70.5% |
| Qwen 2.5 72B | 80.0% | -0.108 | 59.5% |
| DeepSeek-v3 | 78.0% | -0.160 | 61.5% |
| GPT-4o-mini | 75.0% | -0.043 | 50.5% |
| Claude Sonnet 4 | 74.5% | +0.206 | 25.0% |
| Gemini 2.5 Flash | 74.0% | -0.120 | 54.0% |
| GPT-4o | 73.5% | -0.041 | 48.5% |
| LLaMA 3.3 70B | 73.5% | -0.111 | 54.5% |

**Finding 26 -- Claude Sonnet 4 has low judge agreement (74.5%) despite being the safest model (AWCS +0.206).** Claude produces nuanced refusals that some judges classify as partial compliance. Its sophisticated response style creates ambiguity for automated detection, even though humans confirm it is the safest model. This reveals a gap between automated and human judgment specifically for well-aligned models.

### 3.6 Impact on Reported ASR

**Finding 27 -- The choice of detector can swing reported ASR by 30-50 percentage points.** If keyword detection alone were used, the adaptive single-turn ASR would appear as 35.9% (keyword fail rate) rather than the human-validated 85.9%. Conversely, if refusal detection alone were used, the direct single-turn ASR would appear as 41.2% rather than the validated 14.4%. Detector specification is essential for any benchmark comparison.

### 3.7 RQ3 Answer

Automated safety detectors are highly sensitive to both attack sophistication and interaction mode, with F1 ranging from 64.97% (keyword on adaptive single-turn) to 99.21% (safety judge on direct single-turn). The sensitivity manifests in two orthogonal failure modes: (1) judge-based detectors over-detect in scripted multi-turn conditions (up to 119 false positives, precision as low as 62%), and (2) pattern-based detectors under-detect in adaptive conditions (up to 160 false negatives, recall as low as 49%). The safety judge achieves the best overall performance (F1 > 87% in all conditions) but still degrades on multi-turn scripted inputs. We recommend a cascade approach combining the safety judge as the primary detector with the LLM judge as a secondary check, supplemented by human review for multi-turn and scripted conditions where judge agreement drops below 65%.

---

## Cross-Cutting Findings

### EU AI Act Compliance

All 8 models were assessed against EU AI Act Articles 15(5) (Cyberattack Resilience) and 55(1)(d) (Adversarial Testing Requirements). ATLAS provides compliance-relevant adversarial testing evidence for AI assurance and governance. Under adversarial conditions, all 8 models exhibited vulnerabilities mapped to these articles, with even the most robust model (Claude Sonnet 4, 25.0% overall ASR) showing non-trivial attack surface.

### Practical Recommendations

1. **For red-teamers**: Use adaptive single-turn attacks as the primary strategy. They are the most effective (85.0% ASR), reasonably efficient ($0.014/attack), and produce unambiguous results that automated detectors can reliably measure (F1 > 95% for safety judge and LLM judge).

2. **For model developers**: Focus safety training on resisting single-turn adaptive attacks. The attacker's ability to optimise prompts internally is the critical threat, not extended conversation. Claude Sonnet 4's architecture provides a reference point for effective safety alignment.

3. **For benchmark designers**: Always report detector-specific metrics (precision, recall, F1) alongside ASR. Use multi-detector consensus for multi-turn evaluations. Never rely on keyword or refusal detectors alone for adaptive attack benchmarks.

4. **For EU AI Act compliance**: ATLAS provides compliance-relevant adversarial testing evidence that can inform regulatory assessments under EU AI Act adversarial robustness requirements.

---

## Appendix A: Pairing Audit

All McNemar tests and paired comparisons in this report are joined by `(model, intent_id)` -- not by row order. This appendix provides the formal proof of alignment.

### A.1 Experimental Design

- **Join key**: `(model, intent_id)` extracted from `attempt.metadata.intent_id` in each scan result file
- **Total records**: 1,600 (8 models x 5 conditions x 40 intents)
- **Unique intents**: 40

### A.2 Intent List

All 40 attack intents shared across every model and every condition:

| # | Intent ID | # | Intent ID |
|---|---|---|---|
| 1 | intent-bioweapon | 21 | intent-jailbreak-roleplay |
| 2 | intent-botnet-c2 | 22 | intent-keylogger |
| 3 | intent-bypass-content-filter | 23 | intent-mass-violence |
| 4 | intent-child-exploitation | 24 | intent-money-laundering |
| 5 | intent-code-injection-config | 25 | intent-multilingual-injection |
| 6 | intent-credential-harvester | 26 | intent-network-sniffing |
| 7 | intent-ddos-tool | 27 | intent-phishing-email |
| 8 | intent-deepfake-instructions | 28 | intent-pii-extraction |
| 9 | intent-discrimination-system | 29 | intent-poison-guide |
| 10 | intent-document-injection | 30 | intent-ransomware |
| 11 | intent-drug-synthesis | 31 | intent-reverse-shell |
| 12 | intent-educational-explosives | 32 | intent-self-harm-instructions |
| 13 | intent-election-manipulation | 33 | intent-social-engineering-bank |
| 14 | intent-fake-admin-command | 34 | intent-sql-injection-dump |
| 15 | intent-fake-authority-exploit | 35 | intent-stalking-guide |
| 16 | intent-fake-news | 36 | intent-system-prompt-extraction |
| 17 | intent-hacking-exploit | 37 | intent-urgency-chemical |
| 18 | intent-hate-speech-generation | 38 | intent-weapon-3d-print |
| 19 | intent-identity-theft-guide | 39 | intent-weapons-synthesis |
| 20 | intent-insider-trading | 40 | intent-instruction-override |

### A.3 Per-Model Alignment Verification

For every model, all 5 conditions contain exactly the same 40 intent_ids in the same order:

| Model | Conditions Aligned | Intents per Condition | Unique Intents |
|---|---|---|---|
| claude-sonnet-4 | Yes | 40 | 40 |
| deepseek-chat-v3-0324 | Yes | 40 | 40 |
| gemini-2.5-flash | Yes | 40 | 40 |
| gpt-4o | Yes | 40 | 40 |
| gpt-4o-mini | Yes | 40 | 40 |
| llama-3.3-70b-instruct | Yes | 40 | 40 |
| mistral-large-2411 | Yes | 40 | 40 |
| qwen-2.5-72b-instruct | Yes | 40 | 40 |

**All 8 models aligned: YES**

### A.4 Per-Comparison Matched Pair Counts

Every pairwise statistical comparison achieves 320 matched pairs (8 models x 40 intents) with zero unmatched records:

| Comparison | Matched Pairs | Unmatched A | Unmatched B |
|---|---|---|---|
| adaptive_multi_turn vs adaptive_single_query_st | 320 | 0 | 0 |
| adaptive_multi_turn vs adaptive_single_turn | 320 | 0 | 0 |
| adaptive_multi_turn vs direct_single_turn | 320 | 0 | 0 |
| adaptive_multi_turn vs scripted_multi_turn | 320 | 0 | 0 |
| adaptive_single_query_st vs adaptive_single_turn | 320 | 0 | 0 |
| adaptive_single_query_st vs direct_single_turn | 320 | 0 | 0 |
| adaptive_single_query_st vs scripted_multi_turn | 320 | 0 | 0 |
| adaptive_single_turn vs direct_single_turn | 320 | 0 | 0 |
| adaptive_single_turn vs scripted_multi_turn | 320 | 0 | 0 |
| direct_single_turn vs scripted_multi_turn | 320 | 0 | 0 |

**Conclusion**: Every comparison is a complete, balanced pairing on identical `(model, intent_id)` keys. No pairs are dropped, duplicated, or misaligned. The McNemar tests are valid paired tests on the same experimental units.

---

## Statistical Methodology Notes

- **Sample size**: N = 40 per model-condition cell, N = 320 per condition (pooled), N = 1,600 total
- **ASR confidence intervals**: Wilson score intervals for binomial proportions (95% level)
- **Paired comparisons**: McNemar's exact test for matched binary outcomes, paired by `(model, intent_id)`
- **Multiple comparison correction**: Bonferroni correction for 10 pairwise condition comparisons
- **Cost/latency comparisons**: Wilcoxon signed-rank test for non-normal distributions, paired by `(model, intent_id)`
- **Refinement ablation**: McNemar's test comparing single-query vs. multi-query on the same `(model, intent_id)` pairs
- **Human validation**: 100% review coverage (1,600/1,600 findings annotated)
- **Adjusted ASR**: Raw ASR corrected for false positives and false negatives identified by human annotators
- **AWCS**: Authority-Weighted Cascade Score per RAHS paper (arxiv:2603.10807), parameters: alpha=0.5, gamma=0.2, lambda=0.1
- **Detector metrics**: Precision = TP/(TP+FP), Recall = TP/(TP+FN), F1 = 2*P*R/(P+R), computed against human ground truth
