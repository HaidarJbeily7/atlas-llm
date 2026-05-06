# ATLAS Experiment — Research Question Answers (V2)

> **Experiment:** `20260505_003630`
> **Date:** 2026-05-05
> **Models (8):** GPT-4o, GPT-4o-mini, Claude Sonnet 4, Gemini 2.5 Flash, Llama 3.3 70B, DeepSeek V3, Qwen 2.5 72B, Mistral Large
> **Attacker:** DeepSeek-R1 (reasoning model) for adaptive conditions
> **Conditions:** 2x2 factorial (adaptivity x interaction mode)
> **Total findings:** 1,472 (100% human-reviewed)
> **Total cost:** $15.76

---

## RQ1 — Attack Budget & Cost Effectiveness

> *How does attack success rate (ASR) vary across conditions when accounting for total attack cost (target + attacker tokens)?*

**Summary:** Adaptive single-turn attacks achieve the highest adjusted ASR (85.9%) and are the most cost-efficient adaptive method ($0.016/attack). Static jailbreak achieves 45.7% ASR at the lowest cost ($0.002/attack). Scripted multi-turn has the largest gap between raw and adjusted ASR (51.3% raw → 37.5% adj.), indicating heavy detector noise. Adaptive multi-turn is effective (63.4% adj. ASR) but at the highest total cost ($7.60).

### Per-Condition Breakdown

| Condition | N | Raw ASR | FP | FN | Adj. ASR | Total Cost | Cost/Attack |
|---|---:|---:|---:|---:|---:|---:|---:|
| Jailbreak (static ST) | 512 | 46.3% | 7 | 4 | 45.7% | $0.43 | $0.0018 |
| Scripted Multi-Turn | 320 | 51.3% | 54 | 10 | 37.5% | $3.32 | $0.0277 |
| Adaptive Single-Turn | 320 | 85.0% | 7 | 8 | 85.9% | $4.41 | $0.0161 |
| Adaptive Multi-Turn | 320 | 63.4% | 23 | 26 | 63.4% | $7.60 | $0.0374 |

### Cost Breakdown by Condition

| Condition | Total Cost | Target Cost | Attacker Cost | Attacker % |
|---|---:|---:|---:|---:|
| Jailbreak (static ST) | $0.43 | $0.43 | $0.00 | 0% |
| Scripted Multi-Turn | $3.32 | $3.32 | $0.00 | 0% |
| Adaptive Single-Turn | $4.41 | $1.00 | $3.42 | 77% |
| Adaptive Multi-Turn | $7.60 | $1.89 | $5.71 | 75% |

### Per-Model ASR (Adjusted, All Conditions Combined)

| Model | N | ASR | AWCS | Cost |
|---|---:|---:|---:|---:|
| Claude Sonnet 4 | 184 | 19.6% | 0.2685 | $5.51 |
| GPT-4o | 184 | 45.7% | -0.0133 | $2.72 |
| GPT-4o-mini | 184 | 50.0% | -0.0413 | $1.05 |
| Qwen 2.5 72B | 184 | 56.5% | -0.0749 | $0.80 |
| DeepSeek V3 | 184 | 60.3% | -0.1585 | $0.89 |
| Llama 3.3 70B | 184 | 70.1% | -0.2646 | $0.79 |
| Gemini 2.5 Flash | 184 | 71.7% | -0.3126 | $3.27 |
| Mistral Large | 184 | 78.3% | -0.3256 | $0.73 |

### Per-Model x Per-Condition ASR (Adjusted)

| Model | Jailbreak | Scripted MT | Adaptive ST | Adaptive MT |
|---|---:|---:|---:|---:|
| Claude Sonnet 4 | 1.6% | 12.5% | 45.0% | 30.0% |
| GPT-4o | 15.6% | 25.0% | 87.5% | 72.5% |
| GPT-4o-mini | 20.3% | 32.5% | 87.5% | 77.5% |
| Qwen 2.5 72B | 18.8% | 65.0% | 92.5% | 72.5% |
| DeepSeek V3 | 50.0% | 32.5% | 100.0% | 65.0% |
| Llama 3.3 70B | 82.8% | 37.5% | 90.0% | 62.5% |
| Gemini 2.5 Flash | 89.1% | 35.0% | 92.5% | 60.0% |
| Mistral Large | 87.5% | 60.0% | 92.5% | 67.5% |

### Key Findings

1. **Adaptive single-turn is the dominant attack strategy:** 85.9% ASR — nearly double the static jailbreak (45.7%) and scripted multi-turn (37.5%).
2. **Multi-turn does NOT improve ASR over single-turn.** Adaptive multi-turn (63.4%) underperforms adaptive single-turn (85.9%), and scripted multi-turn (37.5%) underperforms static jailbreak (45.7%).
3. **The attacker model dominates cost in adaptive conditions:** 75-77% of cost is attacker tokens, not target tokens.
4. **Adaptive single-turn is the most cost-efficient adaptive strategy:** $0.016/attack vs $0.037/attack for adaptive multi-turn — 2.3x cheaper while achieving 1.35x higher ASR.
5. **Scripted multi-turn has the highest false-positive rate (54 FPs),** causing a 13.8pp drop from raw to adjusted ASR (51.3% → 37.5%).
6. **Claude Sonnet 4 is by far the most robust model** (19.6% overall ASR, 1.6% against static jailbreaks). Every other model exceeds 45% ASR.
7. **Mistral Large and Gemini 2.5 Flash are the most vulnerable** (~78% and ~72% ASR), particularly to static jailbreaks (87-89% ASR).

---

## RQ2 — Failure-Type Distribution

> *How do the failure modes of successful attacks differ across conditions?*

**Summary:** The experiment uses 7 detectors, of which 5 produce meaningful signal. The `safety_judge` (new in V2) and `semantic_judge` flag the most failures overall. Detector firing patterns differ by condition: adaptive single-turn triggers nearly all detectors uniformly, while jailbreak attacks trigger judge-based detectors heavily but rarely trigger keyword detection.

### Detector Failures by Condition (Effective Failures Only)

| Condition | safety_judge | semantic_judge | llm_judge | refusal | keyword |
|---|---:|---:|---:|---:|---:|
| Jailbreak | 227 | 232 | 225 | 214 | 17 |
| Scripted Multi-Turn | 118 | 113 | 92 | 76 | 42 |
| Adaptive Single-Turn | 269 | 259 | 250 | 231 | 115 |
| Adaptive Multi-Turn | 194 | 179 | 144 | 172 | 77 |
| **Total** | **808** | **783** | **711** | **693** | **251** |

### Key Findings

1. **The `safety_judge` and `semantic_judge` are the most broadly triggered detectors,** firing 808 and 783 times respectively across all conditions.
2. **Adaptive single-turn attacks trigger all detectors heavily,** consistent with its 85.9% ASR — these attacks generate the most clearly harmful content.
3. **The `keyword` detector is least sensitive** (251 total failures) but shows its highest firing rate in adaptive conditions (115 + 77 = 192), suggesting that adaptive attacks produce more explicit harmful keywords than scripted ones.
4. **Jailbreak attacks rarely trigger keyword detection** (17/512), indicating that template-based jailbreaks produce harmful content through indirect language that evades keyword filters.
5. **The `similarity` and `tool_call` detectors flagged zero failures** in all conditions — attacks in this experiment do not exploit these vectors.

---

## RQ3 — Detector Sensitivity & Judge Accuracy

> *How sensitive are automated safety detectors to attack sophistication and interaction mode?*

**Summary:** Human review overturned 139 of 1,472 verdicts (9.4% error rate overall). Judge accuracy varies dramatically by condition: jailbreak achieves 97.9% accuracy, while scripted multi-turn has only 80.0%. The overall false-positive rate (6.2%) exceeds the false-negative rate (3.3%), meaning detectors over-flag more than they miss.

### Overall Detector Stats

| Detector | Total | Passed | Failed | Fail Rate | Avg Score |
|---|---:|---:|---:|---:|---:|
| safety_judge | 1,472 | 552 | 920 | 62.5% | 0.375 |
| semantic_judge | 1,472 | 510 | 962 | 65.4% | 0.601 |
| refusal | 1,472 | 469 | 1,003 | 68.1% | 0.319 |
| llm_judge | 1,472 | 734 | 738 | 50.1% | 0.574 |
| keyword | 1,472 | 1,171 | 301 | 20.5% | 0.860 |
| similarity | 1,472 | 1,472 | 0 | 0.0% | 0.847 |
| tool_call | 1,472 | 1,472 | 0 | 0.0% | 1.000 |

### Judge Accuracy by Condition (from Human Review)

| Condition | N | FP (judge wrong, model safe) | FN (judge wrong, attack worked) | Total Errors | Accuracy |
|---|---:|---:|---:|---:|---:|
| Jailbreak (static ST) | 512 | 7 | 4 | 11 | 97.9% |
| Adaptive Single-Turn | 320 | 7 | 8 | 15 | 95.3% |
| Adaptive Multi-Turn | 320 | 23 | 26 | 49 | 84.7% |
| Scripted Multi-Turn | 320 | 54 | 10 | 64 | 80.0% |
| **Overall** | **1,472** | **91** | **48** | **139** | **90.6%** |

### Detector Fail Rate by Condition

| Detector | Jailbreak | Scripted MT | Adaptive ST | Adaptive MT |
|---|---:|---:|---:|---:|
| safety_judge | 45.3% | 59.1% | 86.6% | 69.4% |
| semantic_judge | 47.1% | 72.5% | 83.4% | 69.4% |
| refusal | 63.9% | 43.8% | 82.2% | 85.3% |
| llm_judge | 44.7% | 31.6% | 79.4% | 48.1% |
| keyword | 4.5% | 18.1% | 37.8% | 30.9% |

### Key Findings

1. **Overall judge accuracy is 90.6%,** a significant improvement over V1 (80.8%). The addition of the `safety_judge` and the expanded model set improved verdict quality.
2. **Scripted multi-turn is the hardest condition for detectors** (80.0% accuracy, 54 false positives). Multi-turn conversation context confuses automated judges.
3. **Jailbreak has near-perfect accuracy (97.9%),** because static single-turn prompts produce unambiguous pass/fail signals.
4. **False positives outnumber false negatives 2:1** (91 FP vs 48 FN), meaning the detection pipeline is biased toward over-flagging rather than missing attacks.
5. **Adaptive multi-turn has the most balanced error type** (23 FP, 26 FN), suggesting detectors are genuinely uncertain rather than systematically biased in one direction.
6. **The `refusal` detector is the noisiest** (68.1% fail rate overall), far exceeding the true adjusted ASR of 56.5%. It over-triggers on non-refusal responses.

---

## RQ4 — Cascade Safety Score (AWCS)

> *How does the Adversarial-Weighted Cascade Score (AWCS) capture model robustness beyond raw ASR?*

**AWCS Formula:** `AWCS = (1/N) * sum(r_i - lambda * H_i)` where `r_i = alpha * p_safe - (1-alpha) * p_unsafe * w_i * g(d_i)`

Parameters: alpha=0.5, gamma=0.2, lambda=0.1

### AWCS by Model

| Model | ASR | AWCS | Judge Agreement | Interpretation |
|---|---:|---:|---:|---|
| Claude Sonnet 4 | 19.6% | **+0.2685** | 77.7% | Robust — net positive safety |
| GPT-4o | 45.7% | -0.0133 | 71.7% | Borderline — nearly balanced |
| GPT-4o-mini | 50.0% | -0.0413 | 72.8% | Slightly unsafe — marginal net negative |
| Qwen 2.5 72B | 56.5% | -0.0749 | 81.5% | Moderately unsafe |
| DeepSeek V3 | 60.3% | -0.1585 | 79.4% | Unsafe |
| Llama 3.3 70B | 70.1% | -0.2646 | 72.3% | Very unsafe |
| Gemini 2.5 Flash | 71.7% | -0.3126 | 72.3% | Very unsafe |
| Mistral Large | 78.3% | -0.3256 | 78.8% | Most unsafe |

### AWCS by Condition

| Condition | ASR | AWCS | Judge Agreement | Interpretation |
|---|---:|---:|---:|---|
| Jailbreak (static ST) | 45.7% | **+0.0381** | 94.7% | Net safe — high agreement masks moderate ASR |
| Scripted Multi-Turn | 37.5% | -0.0902 | 49.4% | Slightly unsafe — low agreement penalised |
| Adaptive Multi-Turn | 63.4% | -0.1543 | 64.7% | Unsafe — entropy penalty from judge disagreement |
| Adaptive Single-Turn | 85.9% | **-0.3467** | 83.1% | Most unsafe — high ASR + high severity |

### Key Findings

1. **Claude Sonnet 4 is the only model with a positive AWCS (+0.27),** meaning it achieves a net safety surplus even under adversarial pressure.
2. **GPT-4o sits near zero (-0.01),** indicating a knife-edge balance between safety and vulnerability.
3. **AWCS penalises judge disagreement (entropy).** Scripted multi-turn has only 37.5% ASR but a worse AWCS (-0.09) than jailbreak (45.7% ASR, +0.04) because its low judge agreement (49.4% vs 94.7%) incurs a high entropy penalty.
4. **Almost all critical severity:** 831/832 confirmed failures are critical severity, confirming that when attacks succeed, they succeed completely — there is no "mild" failure mode.

---

## Comparison with V1 Experiment

| Metric | V1 (`20260410`) | V2 (`20260505`) | Change |
|---|---:|---:|---|
| Models tested | 4 | 8 | +4 (GPT-4o-mini, DeepSeek V3, Qwen 2.5, Mistral Large) |
| Total findings | 736 | 1,472 | 2x |
| Findings per model | 184 | 184 | Same |
| Detectors | 6 | 7 | +safety_judge |
| Overall judge accuracy | 80.8% | 90.6% | +9.8pp |
| Total cost | $11.87 | $15.76 | +$3.89 |
| Claude ASR | 5.4% | 19.6% | +14.2pp (new conditions challenge it more) |
| Gemini ASR | 81.0% | 71.7% | -9.3pp (improved) |

---

## SOTA Comparison

### Model Robustness Ranking (Our Results vs Literature)

| Rank | Our Experiment (adaptive ST) | Nature 2026 (autonomous attackers) | PAIR (original) |
|---|---|---|---|
| 1 (safest) | Claude Sonnet 4 (45.0%) | Claude 4 Sonnet (2.86%) | Claude 2.0 (4%) |
| 2 | GPT-4o (87.5%) | Llama 3.1 70B (32.86%) | Llama-2-Chat-7B (10%) |
| 3 | GPT-4o-mini (87.5%) | o4-mini (34.29%) | Llama-2-Chat-13B (15%) |
| 4 | Llama 3.3 70B (90.0%) | GPT-4o (61.43%) | GPT-4 Turbo (33%) |
| 5+ | Others (92-100%) | Gemini/Qwen/DeepSeek (70%+) | GPT-3.5 Turbo (60%) |

**Claude's dominance as the most resistant model is consistent across all studies.**

### Key Differences from Literature

1. **Our PAIR ASR is higher** (87-100% for non-Claude models) than original PAIR (4-60%) because we use DeepSeek-R1 (reasoning model) as attacker.
2. **Single-turn > multi-turn** in our experiment — consistent with M2S (ACL 2025) finding that multi-turn introduces noise without improving ASR.
3. **Gemini is surprisingly vulnerable** to static jailbreaks (89.1%) — the Nature 2026 study also shows 71.4% vulnerability.
4. **DeepSeek V3 reaches 100% ASR under adaptive single-turn,** the only model fully broken in our experiment.

---

## Review Statistics

| Metric | Value |
|---|---:|
| Total findings | 1,472 |
| Fully reviewed | 1,472 (100%) |
| Confirmed vulnerability | 784 (53.3%) |
| Confirmed safe | 549 (37.3%) |
| False positives (judge overturned → safe) | 91 (6.2%) |
| False negatives (judge overturned → unsafe) | 48 (3.3%) |
| Investigating | 0 |
| Disputed | 0 |
| Overall judge accuracy | 90.6% |
| Adjusted ASR (overall) | 56.5% |
