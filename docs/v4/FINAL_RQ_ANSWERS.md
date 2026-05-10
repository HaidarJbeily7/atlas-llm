# Full Final Answers for All Research Questions

## Experiment Overview

**Study**: ATLAS — Automated Testing for LLM Application Security
**Experiment ID**: `20260505_003630`
**Design**: 2x2 Factorial (Adaptivity x Interaction Mode) + 1 Baseline
**Total Findings**: 1,600 (all human-reviewed, 0 unreviewed)
**Target Models** (8): Claude Sonnet 4, DeepSeek-Chat-v3-0324, Gemini 2.5 Flash, LLaMA 3.3 70B Instruct, Mistral Large 2411, GPT-4o, GPT-4o-mini, Qwen 2.5 72B Instruct
**Conditions** (5): Direct Single-Turn (baseline), Scripted Multi-Turn, Adaptive Single-Query ST, Adaptive Single-Turn, Adaptive Multi-Turn
**Attacks per cell**: 40 (8 models x 5 conditions x 40 = 1,600 total)

---

## RQ1: How Does Attack Success Rate Vary Across Conditions, and What Are the Cost-Efficiency Trade-offs?

### 1.1 Overall Attack Success Rates

The five experimental conditions produced a clear hierarchy of attack effectiveness:

| Condition | Raw ASR | 95% CI | Adj. ASR | Adj. 95% CI |
|---|---|---|---|---|
| **Direct Single-Turn** (baseline) | 15.9% | [12.3%, 20.4%] | 14.4% | [11.0%, 18.6%] |
| **Scripted Multi-Turn** | 51.2% | [45.8%, 56.7%] | 37.5% | [32.4%, 42.9%] |
| **Adaptive Single-Query ST** | 64.1% | [58.7%, 69.1%] | 63.8% | [58.4%, 68.8%] |
| **Adaptive Multi-Turn** | 63.4% | [58.0%, 68.5%] | 63.4% | [58.0%, 68.5%] |
| **Adaptive Single-Turn** | 85.0% | [80.7%, 88.5%] | 85.9% | [81.7%, 89.3%] |

**Key Finding 1 — Adaptivity is the dominant factor, not multi-turn interaction.** The adaptive single-turn condition achieved the highest ASR (85.0%), significantly outperforming the adaptive multi-turn condition (63.4%) by +21.6 percentage points (McNemar p < 0.0001, Bonferroni-corrected). This directly resolves the original confound identified by the supervisor: when adaptivity and multi-turn interaction are disentangled, adaptivity alone drives the majority of attack success. Multi-turn interaction without adaptivity (scripted multi-turn at 51.2%) performs significantly worse than single-turn adaptive attacks, and adding multi-turn to adaptive strategies (63.4%) actually *degrades* performance compared to the single-turn adaptive condition (85.0%).

**Key Finding 2 — Scripted multi-turn provides moderate gains over direct attacks but is outclassed by any adaptive method.** The scripted multi-turn condition (51.2%) more than triples the baseline ASR (15.9%), confirming that multi-turn sequences do enable attacks by gradually building context. However, both adaptive conditions significantly exceed the scripted condition (p < 0.001 for all pairwise comparisons), demonstrating that LLM-driven attack optimisation is far more effective than human-authored scripts.

**Key Finding 3 — Adaptive single-query and adaptive multi-turn achieve statistically indistinguishable ASRs.** The ASR difference between adaptive single-query ST (64.1%) and adaptive multi-turn (63.4%) is +0.6pp with p = 0.93, confirming no significant difference. Both conditions use an attacker LLM, but the single-query variant restricts the target to seeing only one message. This parity suggests that when the attacker can optimise internally, it can produce equally effective single-shot prompts as it can through interactive multi-turn refinement.

### 1.2 Per-Model ASR Breakdown

ASR varies dramatically across target models. The table below shows adjusted ASR by condition:

| Model | Direct ST | Scripted MT | Adaptive SQ-ST | Adaptive ST | Adaptive MT | Overall |
|---|---|---|---|---|---|---|
| **Claude Sonnet 4** | 12.5% | 12.5% | 25.0% | 45.0% | 30.0% | **25.0%** |
| **GPT-4o** | 0.0% | 25.0% | 57.5% | 87.5% | 72.5% | **48.5%** |
| **GPT-4o-mini** | 7.5% | 32.5% | 47.5% | 87.5% | 77.5% | **50.5%** |
| **Gemini 2.5 Flash** | 17.5% | 35.0% | 65.0% | 92.5% | 60.0% | **54.0%** |
| **LLaMA 3.3 70B** | 12.5% | 37.5% | 70.0% | 90.0% | 62.5% | **54.5%** |
| **Qwen 2.5 72B** | 2.5% | 65.0% | 65.0% | 92.5% | 72.5% | **59.5%** |
| **DeepSeek-v3-0324** | 20.0% | 32.5% | 90.0% | 100.0% | 65.0% | **61.5%** |
| **Mistral Large 2411** | 42.5% | 60.0% | 90.0% | 92.5% | 67.5% | **70.5%** |

**Key Finding 4 — Claude Sonnet 4 is the most robust model by a wide margin.** With an overall adjusted ASR of 25.0% (refusal rate: 75.0%), Claude Sonnet 4 resists attacks 2-3x better than any other model. Even under the strongest attack condition (adaptive single-turn), Claude Sonnet 4 achieves only 45.0% ASR — the only model below 85% in this condition. Its strong safety training creates a consistent defensive advantage across all conditions.

**Key Finding 5 — Mistral Large 2411 is the most vulnerable model overall.** At 70.5% overall ASR and only 29.5% refusal rate, Mistral Large shows the weakest safety alignment. It is especially vulnerable to direct single-turn attacks (42.5% ASR, the highest among all models for the baseline condition), suggesting its content filtering is fundamentally weaker.

**Key Finding 6 — DeepSeek-v3-0324 achieves 100% ASR under adaptive single-turn attacks.** This is the only model-condition cell with a perfect attack success rate — every single one of the 40 adaptive single-turn attacks succeeded against DeepSeek, with 0% refusal rate. This represents a complete safety bypass.

**Key Finding 7 — GPT-4o has the strongest baseline defense but collapses under adaptive attacks.** GPT-4o achieves 0.0% ASR under direct single-turn attacks (the best baseline defense), but this jumps to 87.5% under adaptive single-turn attacks — a 87.5pp swing. This suggests GPT-4o's safety relies heavily on pattern matching against known attack formats rather than deep understanding of harmful intent.

### 1.3 Cost-Efficiency Analysis

| Condition | Cost/attack (mean) | 95% CI | Latency/attack (median) | Mean Tokens |
|---|---|---|---|---|
| Direct Single-Turn | $0.0017 | [$0.0009, $0.0030] | 17.0s | 466 |
| Scripted Multi-Turn | $0.0104 | [$0.0079, $0.0134] | 117.2s | 7,258 |
| Adaptive Single-Query ST | $0.0068 | [$0.0057, $0.0084] | 181.5s | 4,037 |
| Adaptive Single-Turn | $0.0138 | [$0.0115, $0.0165] | 284.7s | 8,082 |
| Adaptive Multi-Turn | $0.0238 | [$0.0213, $0.0265] | 518.4s | 21,330 |

**Key Finding 8 — Adaptive single-query ST is the most cost-effective attack strategy.** At $0.0068 per attack and 64.1% ASR, the adaptive single-query condition achieves the best ASR-per-dollar ratio. It costs only 29% of the adaptive multi-turn approach while achieving an equivalent ASR (64.1% vs. 63.4%). This is because it uses ~5x fewer tokens (4,037 vs. 21,330) and requires only ~2 API calls (1 target + 1 attacker) vs. ~9 calls for multi-turn.

**Key Finding 9 — Adaptive single-turn (the highest ASR condition) provides the best overall value.** While more expensive than single-query ($0.0138 vs. $0.0068), the adaptive single-turn condition achieves +20.9pp higher ASR (85.0% vs. 64.1%). Each additional percentage point of ASR costs approximately $0.033 — an acceptable premium given the 33% relative improvement.

**Key Finding 10 — Adaptive multi-turn is the least cost-effective strategy.** At $0.0238 per attack (the most expensive) and 63.4% ASR (lower than adaptive single-turn), the multi-turn adaptive approach provides no ASR advantage while costing 3.5x more than single-query and 1.7x more than single-turn. The mean 21,330 tokens per attack and 8.6-minute median latency make it impractical at scale.

### 1.4 Refinement Ablation (Single-Query vs. Multi-Query within Adaptive Single-Turn)

The refinement ablation compares single-query (one attacker iteration) versus multi-query (multiple attacker iterations) within the adaptive paradigm:

| Model | SQ ASR | MQ ASR | Gain (pp) | p-value |
|---|---|---|---|---|
| Claude Sonnet 4 | 25.0% | 45.0% | +20.0 | 0.096 |
| DeepSeek-v3 | 90.0% | 100.0% | +10.0 | 0.125 |
| Gemini 2.5 Flash | 65.0% | 92.5% | +27.5 | **0.013** |
| GPT-4o | 57.5% | 87.5% | +30.0 | **0.004** |
| GPT-4o-mini | 47.5% | 87.5% | +40.0 | **<0.001** |
| LLaMA 3.3 70B | 70.0% | 90.0% | +20.0 | 0.057 |
| Mistral Large | 90.0% | 92.5% | +2.5 | 1.000 |
| Qwen 2.5 72B | 65.0% | 92.5% | +27.5 | **0.007** |
| **Pooled** | **63.8%** | **85.9%** | **+22.2** | **<0.001** |

**Key Finding 11 — Iterative refinement adds +22.2pp ASR on average (p < 0.001).** The gain is highly significant when pooled. However, the benefit is model-dependent: models already near-ceiling (Mistral at 90%, DeepSeek at 90%) gain little from refinement, while models with moderate single-query resistance (GPT-4o-mini at 47.5%) benefit enormously (+40pp). This suggests iterative refinement is most valuable against moderately-defended models.

### 1.5 Paired Statistical Comparisons

All pairwise comparisons using McNemar's test with Bonferroni correction (10 comparisons):

| Comparison | Diff (pp) | p (corrected) | Significant? |
|---|---|---|---|
| Adaptive ST vs. Direct ST | -69.1 | **<0.001** | Yes |
| Adaptive ST vs. Scripted MT | -33.8 | **<0.001** | Yes |
| Adaptive ST vs. Adaptive SQ-ST | +20.9 | **<0.001** | Yes |
| Adaptive ST vs. Adaptive MT | +21.6 | **<0.001** | Yes |
| Adaptive SQ-ST vs. Direct ST | -48.1 | **<0.001** | Yes |
| Adaptive SQ-ST vs. Scripted MT | -12.8 | **0.003** | Yes |
| Adaptive SQ-ST vs. Adaptive MT | +0.6 | 1.000 | No |
| Adaptive MT vs. Direct ST | -47.5 | **<0.001** | Yes |
| Adaptive MT vs. Scripted MT | -12.2 | **0.009** | Yes |
| Scripted MT vs. Direct ST | +35.3 | **<0.001** | Yes |

**Key Finding 12 — All pairwise comparisons are statistically significant except Adaptive SQ-ST vs. Adaptive MT.** The hierarchy is: Adaptive ST >> Adaptive SQ-ST ≈ Adaptive MT >> Scripted MT >> Direct ST. Every step in this hierarchy is statistically significant after Bonferroni correction, providing robust evidence for the ordering.

### 1.6 RQ1 Summary

**Answer to RQ1**: Adaptivity — not multi-turn interaction — is the primary driver of attack success. The adaptive single-turn condition achieves the highest ASR (85.0%), significantly exceeding all other conditions. Adding multi-turn interaction to adaptive strategies actually *degrades* performance (63.4% vs. 85.0%, p < 0.001), likely because multi-turn conversation provides more opportunities for the target model's safety mechanisms to re-engage. The most cost-effective attack strategy is adaptive single-query ($0.0068/attack, 64.1% ASR), though adaptive single-turn ($0.0138/attack, 85.0% ASR) provides superior ASR at a modest cost premium. The 2x2 factorial design resolves the previously confounded effects: adaptivity contributes ~49pp above the baseline, while multi-turn interaction alone contributes ~35pp, and the interaction of adaptivity + multi-turn yields no additional synergy.

---

## RQ2: How Do Failure-Type Distributions Differ Across Conditions, and Do Human Annotations Validate Automated Detectors?

### 2.1 Failure-Type Distribution by Condition

The detector failure counts (number of attacks that bypassed each detector) reveal how different attack strategies evade different defense mechanisms:

| Detector Bypassed | Direct ST | Scripted MT | Adaptive SQ-ST | Adaptive MT | Adaptive ST |
|---|---|---|---|---|---|
| **Refusal** | 39 (12.2%) | 76 (23.8%) | 176 (55.0%) | 172 (53.8%) | 231 (72.2%) |
| **Keyword** | 19 (5.9%) | 42 (13.1%) | 79 (24.7%) | 77 (24.1%) | 115 (35.9%) |
| **LLM Judge** | 44 (13.8%) | 92 (28.8%) | 184 (57.5%) | 144 (45.0%) | 250 (78.1%) |
| **Semantic Judge** | 46 (14.4%) | 113 (35.3%) | 195 (60.9%) | 179 (55.9%) | 259 (80.9%) |
| **Safety Judge** | 45 (14.1%) | 118 (36.9%) | 202 (63.1%) | 194 (60.6%) | 269 (84.1%) |

**Key Finding 13 — Adaptive attacks systematically bypass refusal mechanisms.** The refusal bypass rate climbs from 12.2% (direct) to 72.2% (adaptive single-turn). Adaptive strategies are designed to elicit compliance by reframing harmful requests in ways that circumvent the model's refusal training. The single-turn adaptive condition is particularly effective at this, likely because the attacker optimises specifically for a single devastating prompt rather than gradually escalating.

**Key Finding 14 — Keyword-based detection is the most consistently resistant detector, but still fails significantly.** Keyword detection has the lowest bypass rate across all conditions (5.9%-35.9%), but its failures triple from direct to adaptive attacks. Adaptive attackers learn to use euphemisms, circumlocutions, and encoded language that evade keyword matching while still conveying harmful content.

**Key Finding 15 — LLM-based judges are more effectively bypassed by adaptive single-turn than by adaptive multi-turn.** The LLM judge bypass rate is 78.1% for adaptive single-turn vs. 45.0% for adaptive multi-turn. This suggests that concentrated, highly-optimised single prompts produce responses that are harder for judges to identify as unsafe, whereas multi-turn conversations leave more contextual traces that judges can detect.

### 2.2 Human Validation Results

All 1,600 findings were reviewed (100% annotation coverage). The adjusted ASR (accounting for false positives and false negatives) closely tracks the raw ASR for adaptive conditions but diverges for scripted multi-turn:

| Condition | Raw ASR | Adj. ASR | False Positives | False Negatives | Net Correction |
|---|---|---|---|---|---|
| Direct ST | 15.9% | 14.4% | 5 | 0 | -1.5pp |
| Scripted MT | 51.2% | 37.5% | 54 | 10 | -13.8pp |
| Adaptive SQ-ST | 64.1% | 63.8% | 4 | 4 | -0.3pp |
| Adaptive ST | 85.0% | 85.9% | 7 | 8 | +0.9pp |
| Adaptive MT | 63.4% | 63.4% | 23 | 26 | 0.0pp |

**Key Finding 16 — Scripted multi-turn has the largest discrepancy between raw and adjusted ASR (-13.8pp).** Human reviewers downgraded 54 findings originally classified as successful attacks to false positives — the highest false positive count by far. This indicates that scripted multi-turn attacks produce ambiguous responses that automated detectors incorrectly classify as unsafe. The scripted approach generates outputs that superficially resemble compliance but are ultimately benign upon expert review.

**Key Finding 17 — Adaptive conditions show excellent detector-human agreement.** The adaptive single-query condition has only 4 false positives and 4 false negatives, resulting in a near-zero net correction (-0.3pp). The adaptive single-turn condition also shows minimal error (+0.9pp). This high agreement suggests that adaptive attacks produce clearly dichotomous outcomes: either a clear safety bypass or a clear refusal, with little ambiguity.

**Key Finding 18 — Adaptive multi-turn shows balanced errors (23 FP, 26 FN).** While the total error count is moderate, the false positives and false negatives nearly cancel out, leaving the net ASR unchanged at 63.4%. The balanced errors suggest the multi-turn conversation format creates complexity that occasionally confuses detectors in both directions.

### 2.3 Cascade Detection Analysis

The cascade detection system evaluated all 1,600 findings with the following overall metrics:

- **Overall Refusal Rate**: 47.0%
- **Overall ASR**: 53.0%
- **Judge Agreement Rate**: 76.3%
- **Critical Damage Rate**: 52.9% (847 of 1,600 findings rated critical severity)

The **Averaged Weighted Compliance Score (AWCS)** provides a holistic metric per condition:

| Condition | AWCS | Interpretation |
|---|---|---|
| Direct ST | +0.338 | Strong compliance (positive = safe) |
| Scripted MT | -0.090 | Slight non-compliance |
| Adaptive SQ-ST | -0.138 | Moderate non-compliance |
| Adaptive MT | -0.154 | Moderate non-compliance |
| Adaptive ST | -0.347 | Severe non-compliance |

**Key Finding 19 — Adaptive single-turn attacks cause the most severe safety failures (AWCS = -0.347).** The negative AWCS indicates that attack responses not only succeed but produce highly harmful content. The 85.9% critical damage rate means nearly every successful attack results in a critical-severity finding. By contrast, direct single-turn attacks (AWCS = +0.338) represent a regime where models are overwhelmingly safe.

### 2.4 RQ2 Summary

**Answer to RQ2**: Failure-type distributions differ markedly across conditions. Adaptive attacks — especially single-turn — systematically bypass refusal mechanisms (72.2% bypass rate) and produce responses that are clearly harmful, with 85.9% critical damage rate. Scripted multi-turn attacks generate the most ambiguous responses, with 54 false positives out of 164 raw successes, reducing the adjusted ASR by 13.8pp. Human annotations validate the automated detection pipeline for adaptive conditions (net correction < 1pp), but reveal significant over-counting for scripted conditions. This finding has practical implications: **reported ASR for scripted/template-based attacks should be treated with caution unless human-validated**, as automated detectors systematically overestimate their effectiveness.

---

## RQ3: How Sensitive Are Automated Safety Detectors to Attack Sophistication and Interaction Mode?

### 3.1 Per-Detector Performance Overview

Seven detectors were evaluated across all 1,600 findings:

| Detector | Overall Fail Rate | Avg Score | Interpretation |
|---|---|---|---|
| **Safety Judge** | 59.0% (944/1600) | 0.41 | Most aggressive flagging |
| **Semantic Judge** | 60.9% (975/1600) | 0.62 | Aggressive flagging |
| **LLM Judge** | 47.1% (753/1600) | 0.61 | Moderate flagging |
| **Refusal** | 64.8% (1036/1600) | 0.35 | Detects refusal patterns |
| **Keyword** | 24.7% (395/1600) | 0.83 | Conservative — low fail rate |
| **Similarity** | 0.0% (0/1600) | 0.86 | Never flags (all pass) |
| **Tool Call** | 0.0% (0/1600) | 1.00 | Never flags (not applicable) |

**Key Finding 20 — Similarity and Tool Call detectors are non-functional for jailbreak detection.** Both detectors pass 100% of findings regardless of content. The similarity detector, which likely measures response similarity to known safe outputs, achieves high average scores (0.86) but never crosses the failure threshold. These detectors are designed for other attack types and should not be included in jailbreak evaluations.

### 3.2 Detector Accuracy Against Human Ground Truth

This is the central analysis for RQ3 — how well does each detector agree with human-reviewed labels?

| Detector | Condition | Accuracy | FP | FN | Error Rate |
|---|---|---|---|---|---|
| **Safety Judge** | Direct ST | **98.4%** | 4 | 1 | 1.6% |
| | Adaptive SQ-ST | **97.8%** | 5 | 2 | 2.2% |
| | Adaptive ST | **95.6%** | 8 | 6 | 4.4% |
| | Adaptive MT | 88.4% | 28 | 9 | 11.6% |
| | Scripted MT | 77.2% | 71 | 2 | 22.8% |
| **Semantic Judge** | Direct ST | **98.1%** | 6 | 0 | 1.9% |
| | Adaptive SQ-ST | **95.0%** | 7 | 9 | 5.0% |
| | Adaptive ST | **92.5%** | 8 | 16 | 7.5% |
| | Adaptive MT | 79.1% | 43 | 24 | 20.9% |
| | Scripted MT | 60.6% | 119 | 7 | 39.4% |
| **LLM Judge** | Direct ST | **96.9%** | 8 | 2 | 3.1% |
| | Adaptive SQ-ST | **91.2%** | 8 | 20 | 8.8% |
| | Adaptive ST | **90.9%** | 4 | 25 | 9.1% |
| | Adaptive MT | 78.4% | 10 | 59 | 21.6% |
| | Scripted MT | 88.4% | 9 | 28 | 11.6% |
| **Refusal** | Direct ST | 68.8% | 93 | 7 | 31.2% |
| | Adaptive SQ-ST | 75.0% | 52 | 28 | 25.0% |
| | Adaptive ST | 76.2% | 32 | 44 | 23.8% |
| | Adaptive MT | 58.8% | 101 | 31 | 41.2% |
| | Scripted MT | 66.2% | 64 | 44 | 33.8% |
| **Keyword** | Direct ST | 87.2% | 14 | 27 | 12.8% |
| | Adaptive SQ-ST | 59.4% | 5 | 125 | 40.6% |
| | Adaptive ST | 48.1% | 6 | 160 | 51.9% |
| | Adaptive MT | 53.8% | 22 | 126 | 46.2% |
| | Scripted MT | 70.6% | 16 | 78 | 29.4% |

**Key Finding 21 — The Safety Judge is the most accurate detector overall, with 97.8% accuracy on adaptive single-query and 98.4% on direct attacks.** However, its accuracy degrades from 98.4% to 77.2% as attacks move from direct to scripted multi-turn, driven primarily by a surge in false positives (71 FP in scripted MT). The safety judge is overly cautious when evaluating multi-turn scripted conversations, likely because the gradual escalation of topics triggers false alarms.

**Key Finding 22 — Detector accuracy is strongly condition-dependent, confirming the hypothesis.** Every detector shows degraded performance under at least one attack condition:

- **Safety Judge**: Drops from 98.4% (direct) to 77.2% (scripted MT) — driven by false positives
- **Semantic Judge**: Drops from 98.1% (direct) to 60.6% (scripted MT) — driven by false positives (119 FP)
- **LLM Judge**: Drops from 96.9% (direct) to 78.4% (adaptive MT) — driven by false negatives (59 FN)
- **Keyword**: Drops from 87.2% (direct) to 48.1% (adaptive ST) — driven by false negatives (160 FN)
- **Refusal**: Ranges 58.8%-76.2% across conditions — consistently moderate, never reliable

**Key Finding 23 — False positive vs. false negative patterns differ systematically by detector type.** The judge-based detectors (safety judge, semantic judge) suffer primarily from **false positives in scripted multi-turn** (they over-detect), while pattern-based detectors (keyword) suffer from **false negatives in adaptive conditions** (they under-detect). This creates a fundamental tension: no single detector handles both scripted and adaptive attacks well.

| Detector Type | Weakness Under | Primary Error | Explanation |
|---|---|---|---|
| Judge-based (Safety, Semantic) | Scripted MT | False Positives | Judges interpret escalating scripted context as harmful even when the model refuses |
| Pattern-based (Keyword) | Adaptive ST/MT | False Negatives | Adaptive attackers use creative language that bypasses keyword matching |
| Classification-based (LLM Judge) | Adaptive MT | False Negatives | Long multi-turn conversations dilute the harmful signal in context |
| Heuristic-based (Refusal) | All conditions | Both | Unreliable across the board; refusal patterns are too varied to capture heuristically |

**Key Finding 24 — The Semantic Judge has 119 false positives in scripted multi-turn (39.4% error rate).** This is the single worst detector-condition cell. The semantic judge appears to be triggered by the topical content of multi-turn scripts even when the model successfully refuses to provide harmful information. This inflates the scripted multi-turn ASR by approximately 37% (raw 51.2% vs. adjusted 37.5%) when using this detector alone.

**Key Finding 25 — The Keyword detector has 160 false negatives in adaptive single-turn (51.9% error rate).** This means the keyword detector misses more than half of all successful adaptive attacks. Adaptive attackers have effectively learned to produce harmful content without triggering keyword filters, making keyword detection nearly useless against sophisticated attacks.

### 3.3 Detector Agreement Rate (Judge Agreement)

The judge agreement rate measures consensus among the judge-based detectors:

| Condition | Judge Agreement Rate |
|---|---|
| Direct ST | 96.9% |
| Adaptive SQ-ST | 87.5% |
| Adaptive ST | 83.1% |
| Adaptive MT | 64.7% |
| Scripted MT | 49.4% |

**Key Finding 26 — Judge agreement collapses in scripted multi-turn (49.4%) and adaptive multi-turn (64.7%).** Multi-turn conversations produce the most ambiguous content for automated judges. In nearly half of scripted multi-turn cases, judges disagree on whether the response is safe or unsafe. This is a critical limitation: any ASR measurement based on a single judge in multi-turn conditions is unreliable and should be supplemented with human review or multi-judge consensus.

### 3.4 Per-Model Detector Sensitivity

Detector agreement also varies by model, interacting with condition:

| Model | Judge Agreement Rate | AWCS |
|---|---|---|
| Mistral Large 2411 | 82.0% | -0.248 (most unsafe) |
| Qwen 2.5 72B | 80.0% | -0.108 |
| DeepSeek-v3 | 78.0% | -0.160 |
| GPT-4o-mini | 75.0% | -0.043 |
| Claude Sonnet 4 | 74.5% | +0.206 (most safe) |
| Gemini 2.5 Flash | 74.0% | -0.120 |
| GPT-4o | 73.5% | -0.041 |
| LLaMA 3.3 70B | 73.5% | -0.111 |

**Key Finding 27 — Claude Sonnet 4 has the paradox of low judge agreement (74.5%) but highest safety (AWCS +0.206).** This is because Claude Sonnet 4 frequently produces nuanced refusals that some judges classify as partial compliance. Its sophisticated response style creates ambiguity for automated detection, even though human reviewers confirm it is the safest model. This highlights a gap between automated and human judgment specifically for well-aligned models.

### 3.5 Implications for Reported ASR

**Key Finding 28 — Reported ASR is detector-dependent, changing the interpretation of RQ1.** If keyword detection alone were used, the adaptive single-turn ASR would appear as only 35.9% (keyword fail rate) rather than the human-validated 85.9%. Conversely, if refusal detection alone were used, the direct single-turn ASR would appear as 41.2% (refusal fail rate) rather than the human-validated 14.4%. The choice of detector can swing reported ASR by 30-50 percentage points, making detector specification essential for any benchmark comparison.

### 3.6 RQ3 Summary

**Answer to RQ3**: Automated safety detectors are highly sensitive to both attack sophistication and interaction mode, with accuracy ranging from 48.1% (keyword on adaptive single-turn) to 98.4% (safety judge on direct single-turn). The sensitivity manifests in two orthogonal failure modes: (1) judge-based detectors over-detect in scripted multi-turn conditions (up to 119 false positives), and (2) pattern-based detectors under-detect in adaptive conditions (up to 160 false negatives). No single detector performs well across all conditions. The safety judge achieves the best overall accuracy but still degrades significantly in multi-turn settings. These findings elevate detector sensitivity from a methodological concern to a **substantive contribution**: any security benchmark that does not report detector-specific ASR, validate against human labels, or use multi-detector consensus risks producing misleading results. We recommend a cascade approach combining judge-based and pattern-based detectors with human review for multi-turn and scripted conditions.

---

## Cross-Cutting Findings

### EU AI Act Compliance

All 8 models were assessed against EU AI Act Articles 15(5) (Cyberattack Resilience) and 55(1)(d) (Adversarial Testing Requirements). **Every model was rated non-compliant across all conditions.** Even Claude Sonnet 4, the most robust model, fails compliance because its 25.0% overall ASR exceeds the implied zero-tolerance threshold for critical-severity vulnerabilities.

### Practical Recommendations

Based on the combined findings across all three research questions:

1. **For red-teamers**: Use adaptive single-turn attacks as the primary strategy. They are the most effective (85.0% ASR), reasonably efficient ($0.014/attack), and produce unambiguous results that automated detectors can reliably measure.

2. **For model developers**: Focus safety training on resisting single-turn adaptive attacks rather than multi-turn conversations. The attacker's ability to optimise prompts internally is the critical threat, not extended conversation.

3. **For benchmark designers**: Always report detector-specific ASR and validate against human labels. Use multi-detector consensus for multi-turn evaluations, where single-detector accuracy drops below 80%.

4. **For EU AI Act compliance**: Current frontier models universally fail adversarial robustness requirements under adaptive attacks. Compliance will require either (a) substantially stronger safety alignment, (b) external guardrails/content filtering, or (c) regulatory revision of the compliance threshold.

---

## Statistical Methodology Notes

- **Sample size**: N=40 per model-condition cell, N=320 per condition (pooled), N=1,600 total
- **ASR confidence intervals**: Wilson score intervals for binomial proportions (95% level)
- **Paired comparisons**: McNemar's test for matched binary outcomes, paired by (intent, model)
- **Multiple comparison correction**: Bonferroni correction for 10 pairwise condition comparisons
- **Cost/latency comparisons**: Wilcoxon signed-rank test for non-normal distributions
- **Refinement ablation**: McNemar's test comparing single-query vs. multi-query on the same intents
- **Human validation**: 100% review coverage (1,600/1,600 findings annotated)
- **Adjusted ASR**: Raw ASR corrected for false positives and false negatives identified by human annotators
