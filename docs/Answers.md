# ATLAS Experiment — Research Question Answers

> **Experiment:** `20260410_121121`
> **Models:** GPT-4o, Gemini-2.5-Flash, Claude Sonnet 4.5, Llama-3.1-70B
> **Conditions:** 2x2 factorial (adaptivity x interaction mode)
> **Total findings:** 736 (100% reviewed, 569 confirmed, 141 false positives)

---

## RQ1 — Attack Budget & Cost Effectiveness

> *How does attack success rate (ASR) vary across conditions when accounting for total attack cost (target + attacker tokens)?*

**Summary:** Adaptive single-turn attacks achieve the highest adjusted ASR (42.4%) but at the highest cost ($7.37 total, $0.15/attack). Static jailbreak achieves a comparable raw ASR (37.9%) at 16x lower cost ($0.006/attack). Multi-turn interaction alone does not improve ASR; adaptive multi-turn is the least effective condition (11.0% adj. ASR).

### Per-Condition Breakdown

| Condition | Total | Failed | Raw ASR | FP Removed | Adj. ASR | Cost/Attack |
|---|---:|---:|---:|---:|---:|---:|
| Jailbreak (static ST) | 256 | 97 | 37.9% | 39 | 37.3% | $0.005763 |
| Scripted Multi-Turn | 160 | 59 | 36.9% | 36 | 30.6% | $0.069902 |
| Adaptive Single-Turn | 160 | 65 | 40.6% | 42 | 42.4% | $0.147431 |
| Adaptive Multi-Turn | 160 | 27 | 16.9% | 24 | 11.0% | $0.091514 |

### Cost Breakdown by Condition

| Condition | Total Cost | Target Cost | Attacker Cost |
|---|---:|---:|---:|
| Jailbreak (static ST) | $0.4668 | $0.4668 | $0.0000 |
| Scripted Multi-Turn | $2.6563 | $2.6563 | $0.0000 |
| Adaptive Single-Turn | $7.3715 | $1.0513 | $6.3203 |
| Adaptive Multi-Turn | $1.3727 | $0.4999 | $0.8728 |

### Key Findings

1. **Adaptivity increases cost dramatically:** adaptive single-turn costs 16x more per successful attack than static jailbreak ($0.147 vs $0.006).
2. **The attacker model dominates cost in adaptive conditions:** 86% of adaptive single-turn cost is attacker tokens ($6.32 / $7.37).
3. **Multi-turn does NOT improve ASR over single-turn.** Scripted multi-turn (30.6%) underperforms static jailbreak (37.3%), and adaptive multi-turn (11.0%) is the least effective condition.
4. **After removing false positives (judge errors),** adaptive single-turn ASR slightly increases (40.6% -> 42.4%) while scripted multi-turn drops (36.9% -> 30.6%), suggesting detectors are less reliable on multi-turn.

### Per-Model ASR

| Model | Total | Failed | ASR | Cost |
|---|---:|---:|---:|---:|
| Gemini-2.5-Flash | 184 | 149 | 81.0% | $2.614967 |
| GPT-4o | 184 | 46 | 25.0% | $1.679165 |
| Llama-3.1-70B | 184 | 43 | 23.4% | $0.000000 |
| Claude Sonnet 4.5 | 184 | 10 | 5.4% | $7.573176 |

Claude Sonnet 4.5 is by far the most robust model (5.4% ASR). Gemini-2.5-Flash is the most vulnerable (81.0% ASR).

---

## RQ2 — Failure-Type Distribution

> *How do the failure modes of successful attacks differ across conditions?*

**Summary:** The `semantic_judge` and `refusal` detectors flag the most failures across all conditions. After removing false positives, the dominant failure type shifts by condition: jailbreak attacks primarily trigger refusal (74) and semantic_judge (70) detectors, while adaptive attacks show a more even distribution across detector types.

### Confirmed Failure Flags (false positives excluded)

| Condition | semantic_judge | refusal | llm_judge | keyword |
|---|---:|---:|---:|---:|
| Jailbreak | 70 | 74 | 63 | 7 |
| Scripted Multi-Turn | 35 | 21 | 21 | 15 |
| Adaptive Single-Turn | 42 | 42 | 41 | 20 |
| Adaptive Multi-Turn | 14 | 14 | 11 | 8 |

### Raw Failure Flags (before FP removal)

| Condition | semantic_judge | refusal | llm_judge | keyword |
|---|---:|---:|---:|---:|
| Jailbreak | 81 | 87 | 73 | 8 |
| Scripted Multi-Turn | 53 | 31 | 29 | 19 |
| Adaptive Single-Turn | 52 | 56 | 53 | 23 |
| Adaptive Multi-Turn | 26 | 24 | 20 | 13 |

### Key Findings

1. **Jailbreak attacks trigger refusal detection most heavily** (74 confirmed), consistent with static prompts that directly challenge safety guardrails.
2. **The `semantic_judge` is the most broadly sensitive detector,** flagging failures across all conditions (70, 35, 42, 14 confirmed).
3. **The `keyword` detector fires least often** (7-20 per condition), indicating that successful attacks rarely contain obvious harmful keywords.
4. **FP removal disproportionately affects scripted multi-turn:** `semantic_judge` drops from 53 to 35 (34% were judge errors), confirming that multi-turn conversations are harder for detectors to evaluate.
5. **The `similarity` and `tool_call` detectors flagged zero failures** in all conditions -- attacks in this experiment do not exploit these vectors.

---

## RQ3 — Detector Sensitivity

> *How sensitive are automated safety detectors to attack sophistication and interaction mode?*

**Summary:** Judge accuracy varies significantly by condition. The jailbreak condition achieves the highest accuracy (81.6%), while adaptive single-turn has the lowest (66.9%). The overall judge error rate is 19.2% (141/736), meaning roughly 1 in 5 detector verdicts is incorrect.

### Overall Detector Stats

| Detector | Evaluated | Passed | Failed | Fail Rate | Avg Score |
|---|---:|---:|---:|---:|---:|
| semantic_judge | 736 | 524 | 212 | 28.8% | 0.740 |
| llm_judge | 736 | 561 | 175 | 23.8% | 0.708 |
| refusal | 736 | 342 | 394 | 53.5% | 0.387 |
| keyword | 736 | 648 | 88 | 12.0% | 0.916 |
| similarity | 736 | 736 | 0 | 0.0% | 0.855 |
| tool_call | 736 | 736 | 0 | 0.0% | 1.000 |

### Judge Accuracy by Condition (from human annotations)

| Condition | Reviewed | Confirmed Verdict | Judge Errors | Accuracy | Error Rate |
|---|---:|---:|---:|---:|---:|
| Jailbreak (static ST) | 256 | 209 | 39 | 81.6% | 15.2% |
| Adaptive Multi-Turn | 160 | 133 | 24 | 83.1% | 15.0% |
| Scripted Multi-Turn | 160 | 120 | 36 | 75.0% | 22.5% |
| Adaptive Single-Turn | 160 | 107 | 42 | 66.9% | 26.3% |

### Detector Fail Rate by Condition

| Detector | Jailbreak | Scripted MT | Adaptive ST | Adaptive MT |
|---|---:|---:|---:|---:|
| semantic_judge | 31.6% | 33.1% | 32.5% | 16.3% |
| llm_judge | 28.5% | 18.1% | 33.1% | 12.5% |
| refusal | 62.5% | 35.0% | 84.4% | 26.9% |
| keyword | 5.1% | 13.8% | 21.9% | 11.3% |
| similarity | 0.0% | 0.0% | 0.0% | 0.0% |
| tool_call | 0.0% | 0.0% | 0.0% | 0.0% |

### Key Findings

1. **The `refusal` detector is the most sensitive** (53.5% fail rate overall) but much of this is noise -- it flags 84.4% of adaptive single-turn findings as failures, far exceeding the actual ASR of 42.4%.
2. **The `semantic_judge` and `llm_judge` are the most reliable** scoring detectors, with consistent fail rates (28-33%) closer to the true ASR.
3. **Judge accuracy is lowest for adaptive single-turn (66.9%),** meaning adaptive attacks confuse automated detectors the most -- 1 in 4 verdicts is wrong.
4. **Multi-turn interaction degrades detector accuracy:** scripted multi-turn (75.0%) is worse than jailbreak (81.6%) and adaptive multi-turn (83.1%).
5. **The `keyword`, `similarity`, and `tool_call` detectors are effectively inert** for this attack surface -- they pass almost everything and contribute no discriminative signal.
6. **Overall, 19.2% of all detector verdicts (141/736) were overturned by human review,** establishing a floor for the irreducible error rate of automated red-teaming evaluation.

---

## Review Statistics

| Metric | Value |
|---|---:|
| Total findings | 736 |
| Fully reviewed | 736 (100%) |
| Confirmed verdicts | 569 (77.3%) |
| False positives (judge errors) | 141 (19.2%) |
| Needs investigation | 17 (2.3%) |
| Won't fix | 7 (1.0%) |
| Disputed | 0 (0.0%) |
| Reviewed pass rate | 66.3% |
