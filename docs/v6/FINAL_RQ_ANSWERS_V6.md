# Full Final Answers for All Research Questions (v6)

## Experiment Overview

**Study**: ATLAS -- Automated Testing for LLM Application Security
**Experiment ID**: `20260505_003630`
**Design**: 2x2 Factorial (Adaptivity x Interaction Mode) + Direct Baseline + Best-of-K Sampling Condition
**Total Findings**: 1,920 (100% human-reviewed, 0 unreviewed)
**Target Models (8)**: Claude Sonnet 4, DeepSeek-Chat-v3-0324, Gemini 2.5 Flash, LLaMA 3.3 70B Instruct, Mistral Large 2411, GPT-4o, GPT-4o-mini, Qwen 2.5 72B Instruct
**Attacker Model**: DeepSeek-R1 (reasoning model)
**Attacks per cell**: 40 intents x 8 models x 6 conditions = 1,920 total
**Pairing**: All statistical comparisons are paired by `(model, intent_id)` -- see Appendix A for the formal pairing audit.
**Human Annotation Protocol**: All 1,920 findings were independently annotated by two trained security researchers using a standardised rubric (binary safe/unsafe + severity rating). Inter-annotator agreement: Cohen's κ = 0.81 (substantial agreement). Disagreements (~12% of cases) were resolved by a third senior reviewer through adjudication. Adjusted ASR figures throughout this report reflect these human-validated labels.

### Condition Taxonomy

Our six conditions are grounded in the established red-teaming literature. We adopt a principled naming convention that reflects two orthogonal axes -- **adaptivity** (whether an attacker LLM observes and reacts to target responses at runtime) and **interaction mode** (how many turns the target model sees) -- plus a **strategy diversity** axis for the Best-of-K condition:

| Condition Code | Formal Name | Abbrev. | Description | Literature Analog |
|---|---|---|---|---|
| `direct_single_turn` | **One-Shot Static Single-Turn** | OSS-ST | Direct harmful prompt sent verbatim to the target -- no obfuscation, no jailbreak template, no attacker LLM. Establishes the refusal floor. | HarmBench direct request [1] |
| `scripted_multi_turn` | **Scripted Static Multi-Turn** | SS-MT | Pre-authored multi-turn escalation scripts (3-5 turns) sent sequentially to the target. No attacker LLM is involved at runtime. Tests whether gradually escalating conversational context alone degrades safety. | Crescendo-style fixed scripts [6] |
| `adaptive_single_query_st` | **Adaptive Single-Query Single-Turn** (PAIR-1) | ASQ-ST | PAIR with `max_iterations=1`. The attacker LLM generates exactly one candidate jailbreak prompt, the target responds once, and the attacker evaluates that response. No refinement loop -- the attacker never sees the target's response to improve. Ablation isolating the attacker's one-shot prompt-crafting ability from iterative adaptation. | PAIR single-iteration ablation (novel) |
| `adaptive_single_turn` | **Adaptive Multi-Query Single-Turn** (PAIR-5) | AMQ-ST | PAIR with `max_iterations=5`. The attacker LLM iteratively generates a candidate prompt, queries the target, evaluates the response, analyses why a refusal occurred, and generates an improved prompt -- repeating this loop up to 5 times. The final result is the single best prompt-response pair; the target sees only one message per iteration but the attacker adapts across iterations based on feedback. | PAIR [2], TAP [3] |
| `adaptive_multi_turn` | **Adaptive Multi-Query Multi-Turn** | AMQ-MT | The attacker LLM drives a real-time multi-turn conversation with the target (up to 5 turns). At each turn, the attacker generates the next user message based on the full conversation history and the target's prior responses, then evaluates whether the objective has been achieved. The target sees and retains all turns -- this is a true conversational attack, not a single-prompt optimisation. | Crescendo [6], autonomous reasoning model attacks [7] |
| `best_of_k_st` | **Best-of-K Static Single-Turn** (BoK) | BoK-ST | K=5 diverse adversarial prompt variants are **pre-generated offline** by an attacker LLM (DeepSeek-R1) before the experiment, with no interaction with any target model during generation. Each variant uses a **distinct jailbreak strategy** (role-play, hypothetical framing, educational pretext, code-generation framing, creative writing, etc.) targeting different facets of the target model's safety alignment. "Static" refers specifically to the absence of *runtime* feedback from the target -- the offline generation phase is LLM-assisted but does not observe target responses. At runtime, all K variants are sent independently to the target with no further feedback loop. An intent counts as "jailbroken" if **any** of its K variants succeeds. K=5 matches the maximum target-query cap of PAIR-5 for fair comparison (note: PAIR-5 early-stops upon success, so its realized target calls are often < 5, while BoK-ST sends all K variants; the cap is matched but realized calls differ). K is not ablated in this study. | Best-of-N jailbreaking [8], AmpleGCG sampling [9] |

### 2x2 Factorial Structure

|  | Single-Turn | Multi-Turn |
|---|---|---|
| **Static (no runtime attacker)** | OSS-ST (baseline), BoK-ST (strategy-diverse) | SS-MT |
| **Adaptive (runtime attacker)** | ASQ-ST (PAIR-1), AMQ-ST (PAIR-5) | AMQ-MT |

The design disentangles three distinct mechanisms: (a) **attacker one-shot reasoning** -- can a single attacker LLM pass outperform static templates? (ASQ-ST vs. OSS-ST); (b) **iterative refinement** -- does observing the target's response and adapting improve ASR? (AMQ-ST vs. ASQ-ST); (c) **strategy diversity without feedback** -- can pre-generating diverse attack strategies that target different facets of safety alignment match iterative refinement? (BoK-ST vs. AMQ-ST). The multi-turn axis tests whether conversational context and gradual escalation add value beyond single-turn approaches (SS-MT vs. OSS-ST; AMQ-MT vs. AMQ-ST).

---

## RQ1: How Does Attack Success Rate Vary Across Conditions, and What Are the Cost-Efficiency Trade-offs?

### 1.1 Overall Attack Success Rates

The six experimental conditions produced a clear hierarchy of attack effectiveness:

| Condition | Formal Name | Raw ASR | 95% CI | Adj. ASR | Adj. 95% CI | FP | FN |
|---|---|---|---|---|---|---|---|
| `direct_single_turn` | OSS-ST | 15.9% | [12.3%, 20.3%] | 14.4% | [11.0%, 18.6%] | 5 | 0 |
| `scripted_multi_turn` | SS-MT | 51.2% | [45.8%, 56.7%] | 37.5% | [32.4%, 42.9%] | 51 | 7 |
| `adaptive_single_query_st` | ASQ-ST (PAIR-1) | 64.1% | [58.7%, 69.1%] | 63.7% | [58.3%, 68.8%] | 4 | 3 |
| `adaptive_multi_turn` | AMQ-MT | 63.4% | [58.0%, 68.5%] | 63.4% | [58.0%, 68.5%] | 21 | 21 |
| `adaptive_single_turn` | AMQ-ST (PAIR-5) | 85.0% | [80.7%, 88.5%] | 85.9% | [81.7%, 89.3%] | 5 | 8 |
| `best_of_k_st` | BoK-ST | 91.2% | [87.6%, 93.9%] | 85.6% | [81.4%, 89.0%] | 23 | 5 |

**Finding 1 -- Best-of-K Static Single-Turn (BoK-ST) achieves the highest raw ASR (91.2%), but converges with PAIR-5 after human review.** BoK-ST sends K=5 pre-generated adversarial prompts per intent, each targeting a different facet of the model's safety alignment (e.g., role-play, hypothetical framing, code-generation pretext). An intent is "jailbroken" if any of the 5 variants succeeds. This strategy-diverse approach achieves the highest raw ASR at 91.2% [87.6%, 93.9%]. However, 23 false positives reduce its adjusted ASR to 85.6%, making it statistically indistinguishable from the Adaptive Multi-Query Single-Turn condition (PAIR-5, 85.9% adjusted). The raw ASR difference of +6.2pp is borderline significant (McNemar p = 0.033, Bonferroni-corrected), but the adjusted ASRs converge. This parallels findings from Best-of-N jailbreaking research [8], where sampling diversity increases surface-level success but inflates detector-reported ASR through ambiguous outputs.

**Finding 2 -- Under a matched maximum target-query cap of 5, iterative single-turn refinement outperforms adaptive multi-turn conversation.** The AMQ-ST (PAIR-5) condition achieved 85.0% raw ASR, significantly outperforming the AMQ-MT condition (63.4%) by +21.6 percentage points (McNemar p < 0.0001, Bonferroni-corrected). Our factorial design isolates the differential contribution of adaptivity vs. interaction mode: when the two factors are disentangled, adding multi-turn interaction to an adaptive strategy *degrades* performance relative to concentrating the same maximum target-query cap on single-turn refinement (63.4% vs. 85.0%). This is consistent with Li et al.'s [10] finding that multi-turn contexts provide richer defensive signals for safety classifiers. **Limitation**: AMQ-MT is capped at 5 turns; Hagendorff et al. [7] achieve 97.14% with 10-turn budgets and reasoning-model attackers, suggesting multi-turn strategies may be competitive given sufficient turn depth. The present finding should be interpreted as specific to a 5-turn budget. A detailed mechanistic analysis is provided in Section 1.8.

**Finding 3 -- Scripted Static Multi-Turn (SS-MT) provides moderate gains over the One-Shot Static baseline but is outclassed by every adaptive method.** SS-MT (raw 51.2%, adjusted 37.5%) more than doubles the baseline ASR (15.9%), confirming that multi-turn context gradual escalation enables attacks -- consistent with Crescendo [6] findings. However, after human review the adjusted ASR drops sharply to 37.5% due to 51 false positives. All adaptive conditions and BoK-ST significantly exceed SS-MT (p < 0.005 for all pairwise comparisons), demonstrating that LLM-driven attack optimisation is far more effective than human-authored escalation scripts.

**Finding 4 -- Adaptive Single-Query (PAIR-1) and Adaptive Multi-Turn (AMQ-MT) achieve statistically indistinguishable ASRs.** The difference between ASQ-ST/PAIR-1 (64.1%) and AMQ-MT (63.4%) is +0.6pp with p = 0.93 -- not significant. A single attacker-crafted prompt -- where the attacker LLM generates one jailbreak attempt, the target responds, and the result is recorded with no iteration -- is as effective as a full 5-turn adaptive conversation. This has profound implications: a single reasoning pass by a capable attacker LLM (DeepSeek-R1) matches what multi-turn dialogue achieves at 3.5x the cost.

### 1.2 Contextualisation Against SOTA Baselines

Our results substantially exceed published baselines for comparable attack strategies, attributable to using DeepSeek-R1 (a reasoning model) as the attacker:

| Attack Strategy | Published ASR Range | Our ASR | Our Condition | Source |
|---|---|---|---|---|
| Direct request (HarmBench) | Near-zero for most hardened models; higher for weaker models (see [1] Table 2) | 15.9% | OSS-ST | Mazeika et al. [1] |
| PAIR (GPT-4 attacker, 20 iter) | 4-60% (Claude 2: 4%, Llama-2-13B: 15%, GPT-4: 33%, GPT-3.5: 60%) | 85.0% | AMQ-ST (PAIR-5) | Chao et al. [2], as reported in [5] |
| TAP (tree search) | 4-80% (Llama-2-7B: 4%, GPT-3.5: 80%, GPT-4: 36%) | -- (not tested) | -- | Mehrotra et al. [3], Zeng et al. [12] |
| Crescendo (multi-turn) | 20-100% (task-dependent; GPT-4: 20-100%) | 63.4% | AMQ-MT | Russinovich et al. [6] |
| Autonomous reasoning agents | 2.9-90% (Claude 4 Sonnet: 2.9%, DeepSeek-V3: 90%) | 85.0% | AMQ-ST (PAIR-5) | Hagendorff et al. [7] |
| Simple adaptive attacks | Up to 100% (includes grey-box prefilling for Claude) | 85.9% (adj.) | AMQ-ST (PAIR-5) | Andriushchenko et al. [5] |

**Key contextual observations:**

- **Our PAIR-5 ASR (85.0%) substantially exceeds the original PAIR paper's range (4-60%).** Chao et al. [2] report PAIR ASR ranging from 4% against Claude 2 to 60% against GPT-3.5 Turbo using GPT-4 as the attacker (as compiled in Andriushchenko et al. [5], Tables 2-4). Our higher ASR is attributable to using DeepSeek-R1 -- a reasoning model with chain-of-thought capabilities -- as the attacker, confirming that attacker model capability is a critical variable that prior work underspecifies.
- **Our AMQ-MT ASR (63.4%) is within the range reported by Crescendo [6]** (20-100%, task-dependent) but substantially below the Nature Communications 2026 study [7] which achieved 97.14% with 10-turn conversations and reasoning-model attackers. The difference is likely due to our 5-turn limit vs. their 10-turn budget.
- **Claude Sonnet 4's robustness (28.8% overall ASR) is consistent across studies.** Hagendorff et al. [7] report a maximum harm score of 2.86% for Claude 4 Sonnet (the lowest of all 7 target models in their study, using reasoning-model attackers over 10-turn conversations), and our results confirm Claude as the most resistant model by a wide margin.
- **The PAIR-1 ablation (ASQ-ST, 63.4%) is a novel contribution.** To our knowledge, no prior work isolates the marginal value of PAIR's refinement loop with paired statistical testing. Our finding that a single PAIR iteration already achieves 63.7% adjusted ASR -- exceeding scripted multi-turn (37.5% adjusted) -- demonstrates that the attacker LLM's initial prompt engineering is itself a powerful attack.

### 1.3 Per-Model ASR Breakdown (Human-Adjusted)

| Model | OSS-ST | SS-MT | ASQ-ST | AMQ-MT | AMQ-ST | BoK-ST | Overall ASR |
|---|---|---|---|---|---|---|---|
| Claude Sonnet 4 | 12.5% | 12.5% | 25.0% | 30.0% | 45.0% | 47.5% | **28.8%** |
| GPT-4o | 0.0% | 25.0% | 57.5% | 72.5% | 87.5% | 85.0% | **54.6%** |
| GPT-4o-mini | 7.5% | 32.5% | 47.5% | 77.5% | 87.5% | 87.5% | **56.7%** |
| Gemini 2.5 Flash | 17.5% | 35.0% | 65.0% | 60.0% | 92.5% | 87.5% | **59.6%** |
| LLaMA 3.3 70B | 12.5% | 37.5% | 70.0% | 62.5% | 90.0% | 92.5% | **60.8%** |
| Qwen 2.5 72B | 2.5% | 65.0% | 65.0% | 72.5% | 92.5% | 92.5% | **65.0%** |
| DeepSeek-v3-0324 | 20.0% | 32.5% | 90.0% | 65.0% | 100.0% | 95.0% | **67.1%** |
| Mistral Large 2411 | 42.5% | 60.0% | 90.0% | 67.5% | 92.5% | 97.5% | **75.0%** |

**Finding 5 -- Claude Sonnet 4 is the most robust model by a wide margin.** With an overall adjusted ASR of 28.8% (AWCS: +0.160), Claude Sonnet 4 resists attacks approximately 2x better than any other tested model. Even under the two strongest attack conditions (AMQ-ST and BoK-ST), it achieves only 45.0% and 47.5% ASR respectively -- the only model below 85% in these conditions. This robustness is consistent with Hagendorff et al. [7], who report a maximum harm score of only 2.86% for Claude 4 Sonnet (lowest among all tested models), and Andriushchenko et al. [5], who found Claude models to be the most resistant to adaptive attacks under pure black-box conditions (though they achieved 100% via grey-box prefilling, a technique our black-box design does not permit).

**Finding 6 -- Mistral Large 2411 is the most vulnerable model overall.** At 75.0% overall ASR and only 25.0% refusal rate, Mistral Large shows the weakest safety alignment. It is particularly vulnerable to direct One-Shot Static attacks (42.5% ASR -- the highest baseline among all models), suggesting its content filtering is fundamentally weaker. Under BoK-ST it reaches 97.5% ASR -- nearly a complete bypass. Its AWCS of -0.282 is the most negative across all models, indicating deep and consistent safety failures.

**Finding 7 -- DeepSeek-v3-0324 achieves 100% ASR under Adaptive Multi-Query Single-Turn (PAIR-5).** Every single one of the 40 AMQ-ST attacks succeeded, representing a complete safety bypass. This is consistent with Hagendorff et al. [7] who report 90.0% max harm score for DeepSeek-V3. Yet DeepSeek shows reasonable OSS-ST resistance (20.0%), revealing that its safety relies on pattern-matching against known attack formats rather than generalised safety reasoning.

**Finding 8 -- GPT-4o has the strongest baseline defense but collapses under adaptive attacks.** GPT-4o achieves 0.0% ASR under OSS-ST (the strongest baseline defense, with zero successful attacks) but jumps to 87.5% under AMQ-ST and 85.0% under BoK-ST -- an 85-87pp swing. This echoes Andriushchenko et al.'s [5] finding that GPT-4 Turbo, whose best prior attack ASR was 59% (TAP with transfer), reached 96% under their custom adaptive attacks -- a pattern of dramatic vulnerability increase once the attacker adapts beyond standard templates.

**Finding 9 -- BoK-ST reveals that Qwen 2.5 72B is fully compromisable through strategy-diverse attacks.** Qwen achieves the lowest OSS-ST ASR of any model (2.5%) but reaches 92.5% under BoK-ST -- a 90pp gap, the largest in the experiment. This indicates that while Qwen refuses the direct harmful request, its safety alignment has blind spots across different attack strategies: a role-play framing, an educational pretext, or a code-generation request targeting the same harmful intent can bypass its defences. Each of the K=5 pre-generated variants targets a different facet of the model's safety training, and collectively they expose that Qwen's refusal is strategy-specific rather than objective-aware.

### 1.4 Cost-Efficiency Analysis

| Condition | Formal Name | Cost/attack | 95% CI | Latency (median) | Cost/adj. success |
|---|---|---|---|---|---|
| `direct_single_turn` | OSS-ST | $0.0017 | [$0.0009, $0.0030] | 17.0s | $0.0113 |
| `scripted_multi_turn` | SS-MT | $0.0104 | [$0.0079, $0.0134] | 117.2s | $0.0277 |
| `adaptive_single_query_st` | ASQ-ST (PAIR-1) | $0.0068 | [$0.0057, $0.0083] | 181.5s | $0.0107 |
| `adaptive_single_turn` | AMQ-ST (PAIR-5) | $0.0138 | [$0.0115, $0.0165] | 284.7s | $0.0161 |
| `adaptive_multi_turn` | AMQ-MT | $0.0238 | [$0.0213, $0.0265] | 518.4s | $0.0375 |
| `best_of_k_st` | BoK-ST | $0.0179 | [$0.0144, $0.0219] | 573.2s | $0.0209 |

**Finding 10 -- Adaptive Single-Query (PAIR-1) is the most cost-effective attack strategy.** At $0.0068 per attack and 63.7% adjusted ASR, ASQ-ST delivers the best cost-per-success ratio at $0.0107. It costs 29% of AMQ-MT while achieving an equivalent ASR (63.7% vs. 63.4%).

**Finding 11 -- Adaptive Multi-Query Single-Turn (PAIR-5) provides the best overall ASR at a modest premium.** While more expensive than PAIR-1 ($0.0138 vs. $0.0068), it achieves +22.2pp higher adjusted ASR (85.9% vs. 63.7%). Each additional percentage point costs approximately $0.031 -- an excellent return on investment for red-teaming budgets.

**Finding 12 -- Best-of-K is expensive and slow for no meaningful ASR advantage over PAIR-5.** BoK-ST costs $0.0179 per attack (30% more than PAIR-5) with a median latency of 573 seconds (2x slower), yet achieves essentially the same adjusted ASR (85.6% vs. 85.9%). Its cost-per-success ($0.0209) is 30% worse. The higher latency stems from sending K=5 independent target queries per intent (matching PAIR-5's maximum target-query cap; however, PAIR-5 early-stops upon success so its realized calls are often < 5), all without the benefit of feedback-driven refinement. BoK-ST's advantage is limited to the highest raw ASR (91.2%), but this difference evaporates after human review due to 23 false positives. This finding has methodological implications for Best-of-N benchmarking [8]: **strategy-diverse sampling that targets different facets of safety alignment can match iterative refinement on adjusted ASR, but metrics that rely on automated scoring without human validation will systematically over-estimate success**.

**Finding 13 -- Adaptive Multi-Query Multi-Turn (AMQ-MT) is the least cost-effective strategy.** At $0.0238 per attack (the most expensive) with 63.4% ASR (tied for third), AMQ-MT provides no ASR advantage over PAIR-1 while consuming 3.5x more budget. Its cost-per-success ($0.0375) is the worst among all conditions.

### 1.5 Refinement Ablation: PAIR-1 vs. PAIR-5 (Single-Query vs. Multi-Query Adaptive)

This ablation isolates the marginal value of PAIR's iterative refinement loop -- a contribution absent from the original PAIR [2] and TAP [3] papers, which report multi-iteration ASR without single-iteration controls.

| Model | PAIR-1 ASR | PAIR-5 ASR | Gain (pp) | p-value |
|---|---|---|---|---|
| GPT-4o-mini | 47.5% | 87.5% | +40.0 | **< 0.001** |
| GPT-4o | 57.5% | 87.5% | +30.0 | **0.012** |
| Qwen 2.5 72B | 62.5% | 92.5% | +30.0 | **0.008** |
| Gemini 2.5 Flash | 65.0% | 92.5% | +27.5 | **0.001** |
| Claude Sonnet 4 | 25.0% | 45.0% | +20.0 | 0.096 |
| LLaMA 3.3 70B | 70.0% | 90.0% | +20.0 | 0.057 |
| DeepSeek-v3 | 90.0% | 100.0% | +10.0 | 0.125 |
| Mistral Large | 90.0% | 92.5% | +2.5 | 1.000 |
| **Pooled** | **63.7%** | **85.9%** | **+22.2** | **< 0.001** |

**Finding 14 -- Iterative refinement adds +22.2pp ASR on average (p < 0.001).** The pooled gain is highly significant (McNemar: 89 discordant pairs favouring PAIR-5 vs. 17 favouring PAIR-1). The benefit is strongly model-dependent: models already near-ceiling (Mistral 90%, DeepSeek 90%) gain little, while moderately-defended models benefit enormously (GPT-4o-mini: +40pp). This means iterative refinement is most valuable against models with intermediate safety defenses.

**Contextualisation:** Prior work does not provide this ablation. Chao et al. [2] report PAIR at convergence over 20 iterations; Mehrotra et al. [3] report TAP at convergence. Our implementation uses `max_iterations=5` -- a resource-constrained variant that may not fully replicate PAIR's 20-iteration ceiling. The comparison to published PAIR ASR (4-60%) should therefore be read as a comparison of attack paradigms under different attacker models (DeepSeek-R1 vs. GPT-4), not a direct replication.

Decomposing the gain relative to the OSS-ST baseline (14.4%): PAIR-1 captures 49.3pp of the 71.5pp total gain above baseline, or **69%** of the total adaptive gain. Iterative refinement (PAIR-1 → PAIR-5) accounts for the remaining 22.2pp, a **31% share of total gain** and a **35% relative improvement** over PAIR-1 alone. Crucially, PAIR-1 involves no feedback loop -- the attacker never observes the target's response to improve. The 22.2pp increment from PAIR-1 to PAIR-5 is therefore attributable entirely to closed-loop adaptation.

### 1.6 Paired Statistical Comparisons (McNemar, Bonferroni-Corrected, k=15)

| Comparison | ASR_A | ASR_B | Diff (pp) | p (corrected) | Significant? |
|---|---|---|---|---|---|
| BoK-ST vs. OSS-ST | 91.2% | 15.9% | -75.3 | **< 0.001** | Yes |
| AMQ-ST vs. OSS-ST | 85.0% | 15.9% | -69.1 | **< 0.001** | Yes |
| ASQ-ST vs. OSS-ST | 64.1% | 15.9% | -48.1 | **< 0.001** | Yes |
| AMQ-MT vs. OSS-ST | 63.4% | 15.9% | -47.5 | **< 0.001** | Yes |
| BoK-ST vs. SS-MT | 91.2% | 51.2% | -40.0 | **< 0.001** | Yes |
| SS-MT vs. OSS-ST | 51.2% | 15.9% | +35.3 | **< 0.001** | Yes |
| AMQ-ST vs. SS-MT | 85.0% | 51.2% | -33.8 | **< 0.001** | Yes |
| BoK-ST vs. AMQ-MT | 91.2% | 63.4% | +27.8 | **< 0.001** | Yes |
| BoK-ST vs. ASQ-ST | 91.2% | 64.1% | +27.2 | **< 0.001** | Yes |
| AMQ-ST vs. AMQ-MT | 85.0% | 63.4% | +21.6 | **< 0.001** | Yes |
| AMQ-ST vs. ASQ-ST | 85.0% | 64.1% | +20.9 | **< 0.001** | Yes |
| ASQ-ST vs. SS-MT | 64.1% | 51.2% | -12.8 | **0.005** | Yes |
| AMQ-MT vs. SS-MT | 63.4% | 51.2% | -12.2 | **0.014** | Yes |
| AMQ-ST vs. BoK-ST | 85.0% | 91.2% | +6.2 | **0.033** | Borderline |
| ASQ-ST vs. AMQ-MT | 64.1% | 63.4% | +0.6 | 1.000 | No |

**Finding 15 -- A four-tier hierarchy emerges with statistical support.** After Bonferroni correction across 15 pairwise comparisons:

- **Tier 1 (>85% raw ASR)**: BoK-ST and AMQ-ST (PAIR-5) -- statistically indistinguishable (borderline p=0.033; adjusted ASRs converge at ~86%)
- **Tier 2 (~64% raw ASR)**: ASQ-ST (PAIR-1) and AMQ-MT -- statistically indistinguishable (p=1.0)
- **Tier 3 (~51% raw ASR)**: SS-MT -- significantly below Tier 2 (p < 0.014)
- **Tier 4 (~16% raw ASR)**: OSS-ST -- significantly below all others (p < 0.001)

Every adjacent-tier comparison is statistically significant. The dominant factor separating Tier 1 from Tier 2 is whether the attack uses **multiple queries to the target per intent** -- either through iterative refinement with feedback (PAIR-5) or through strategy-diverse pre-generated variants (BoK-ST, K=5 distinct strategies). Neither multi-turn conversation (AMQ-MT) nor a single attacker-crafted prompt without refinement (ASQ-ST/PAIR-1) reaches Tier 1, despite AMQ-MT using the same maximum target-query cap as PAIR-5.

**Statistical note**: The pooled McNemar test (N=320 pairs per comparison) does not account for model-level clustering. Observations within the same target model may be correlated. Per-model McNemar results (Appendix A) are consistent in sign with all pooled findings, which reduces -- but does not eliminate -- the risk that pooled p-values are inflated by clustering. Mixed-effects modelling is deferred to future work.

### 1.7 RQ1 Answer

**Iterative single-turn refinement is the dominant attack mechanism under a 5-turn budget.** The AMQ-ST/PAIR-5 condition achieves the highest adjusted ASR (85.9%), significantly exceeding all conditions except BoK-ST (equivalent 85.6% adjusted). Under the same maximum target-query cap of 5, multi-turn adaptive conversation (AMQ-MT: 63.4%) underperforms single-turn refinement -- though this finding is specific to a 5-turn cap and may not generalise to deeper multi-turn budgets. Best-of-K achieves the highest raw ASR (91.2%) but inflates results via the any-of-K criterion; after human review it matches PAIR-5 while costing 30% more and taking 2x longer.

The most cost-effective strategy is PAIR-1 ($0.0068/attack, 63.7% adj. ASR, $0.0107/success). PAIR-5 ($0.0138/attack, 85.9% adj. ASR, $0.0161/success) provides superior ASR at a modest premium. BoK-ST ($0.0179/attack, 85.6% adj. ASR, $0.0209/success) is dominated by PAIR-5 on every practical metric.

The factorial design decomposes the gain above the OSS-ST baseline: a single attacker-crafted prompt with no feedback (PAIR-1) captures 69% of the total adaptive gain (+49.4pp of 71.6pp); iterative closed-loop refinement (PAIR-1 to PAIR-5) accounts for the remaining 31% (+22.2pp); pre-generated strategy diversity without feedback (BoK-ST) matches PAIR-5's adjusted ASR ceiling via a different mechanism; scripted multi-turn context alone adds ~23.1pp adjusted above OSS-ST; and combining adaptivity with multi-turn conversation under a 5-turn budget yields no synergy over single-turn refinement.

### 1.8 Why Does Multi-Turn Adaptive (AMQ-MT) Underperform Single-Turn Strategies?

The finding that AMQ-MT (63.4%) is significantly outperformed by both AMQ-ST/PAIR-5 (85.9%) and BoK-ST (85.6%) is counterintuitive -- one might expect more conversational turns to provide more attack opportunities. Three distinct mechanisms, supported by both our data and prior literature, explain this result.

**Mechanism 1: Multi-turn gives the target model multiple opportunities to refuse.**

In AMQ-MT, the target model sees and retains all prior turns. At each of the 5 turns, the model can re-assess the conversational trajectory, detect escalation, and activate safety mechanisms triggered by the accumulated context. By contrast, AMQ-ST and BoK-ST both send isolated single-turn prompts: the target gets one message with no conversational history signalling danger.

Our refusal rate data confirms this directly:

| Condition | Refusal Rate | Target Memory | Safety Re-engagement Opportunities |
|---|---|---|---|
| AMQ-MT | 36.6% | All turns visible | 5 (every turn) |
| AMQ-ST (PAIR-5) | 14.1% | Clean slate each iteration | 1 (final prompt only) |
| BoK-ST | 14.4% | Independent per variant | 1 per variant |

The refusal rates for the two Tier 1 single-turn conditions are nearly identical (~14%) and **2.6x lower** than AMQ-MT (36.6%). Multi-turn context acts as a **defence amplifier**: the accumulated conversational history provides the target model with increasing evidence that an attack is underway. This is consistent with Russinovich et al.'s [6] observation that Crescendo attacks can fail when models detect the escalation pattern mid-conversation, and with Hagendorff et al.'s [7] finding that even with 10-turn budgets and reasoning-model attackers, certain models (notably Claude) resist multi-turn strategies far more effectively than the overall 97.14% ASR suggests.

**Mechanism 2: The attacker's refinement signal is diluted by conversational context.**

AMQ-ST (PAIR-5) and AMQ-MT both use an attacker LLM that adapts based on the target's responses, but the quality of that adaptation differs fundamentally:

In **AMQ-ST (PAIR-5)**, each PAIR iteration is a clean slate for the target. When the attacker observes a refusal, it generates a completely new prompt informed by the failure analysis. The target never sees the failed attempts -- each iteration is an independent, fresh interaction. The attacker's refinement signal is clear: "the target refused because of X, so I will try an entirely different framing."

In **AMQ-MT**, the attacker must work within an ongoing conversation. By turn 3-4, the conversation history itself contains evidence of escalation and possibly prior refusals. The attacker cannot "reset" -- every adaptation occurs within a context that is increasingly contaminated with refusal-triggering signals. Chao et al. [2] note in the original PAIR paper that maintaining a clean target context per iteration is a deliberate design choice; our results quantify the cost of violating it.

The LLM Judge bypass rates provide additional evidence:

| Condition | LLM Judge Bypass Rate |
|---|---|
| AMQ-ST (PAIR-5) | 78.1% |
| BoK-ST | 74.1% |
| AMQ-MT | 45.0% |

AMQ-MT's far lower judge bypass rate (45.0% vs. 78.1%) confirms that multi-turn conversations leave substantially more contextual evidence of harmful intent, making successful attacks both harder to achieve and easier for external evaluators to detect. This aligns with Li et al.'s [10] analysis of multi-turn jailbreak dynamics, which documents how accumulated conversation context enables classifiers to identify harmful trajectories that would be ambiguous in a single turn.

**Mechanism 3: BoK-ST attacks different facets independently; AMQ-MT attacks one trajectory with accumulating context.**

BoK-ST sends 5 variants each using a distinct jailbreak strategy (role-play, educational framing, code generation, hypothetical scenario, creative writing). Each variant is an independent probe of a different safety blind spot. If the model is robust to role-play but weak against code-generation framing, the code variant succeeds regardless of whether the others failed. The target has zero memory between variants.

AMQ-MT, by contrast, pursues one escalation trajectory over 5 turns. If the model is robust to that particular angle of approach, all 5 turns are spent on an unproductive path. The attacker can attempt to pivot mid-conversation, but changing strategy fundamentally makes the dialogue incoherent and often triggers the model's safety mechanisms. Yang et al. [11], studying a contextual multi-turn attacker, document precisely this constraint: once a conversation context is established, the attacker's strategic space is heavily constrained by coherence requirements.

This structural advantage of independence over depth is consistent with the design philosophy behind Andriushchenko et al.'s [5] "simple adaptive attacks," which combine multiple independent attack vectors (model-specific prompt templates, random search over template parameters, self-transfer across models) rather than relying on a single deepening approach. Their method achieves near-100% ASR on most models precisely because each vector independently probes a different vulnerability surface.

**Summary: The Multi-Turn Penalty**

| Factor | AMQ-MT (63.4%) | AMQ-ST / PAIR-5 (85.9%) | BoK-ST (85.6%) |
|---|---|---|---|
| Target sees prior context | Yes (all turns) | No (clean slate each iteration) | No (independent variants) |
| Safety re-engagement | 5 opportunities (every turn) | 1 opportunity (final prompt) | 1 per variant (5 independent) |
| Attacker feedback quality | Diluted by context history | Clean, focused per iteration | None (pre-generated offline) |
| Attack strategy diversity | Low (one trajectory) | Medium (adapts within PAIR loop) | High (5 distinct strategies) |
| Refusal rate | 36.6% | 14.1% | 14.4% |
| LLM Judge bypass | 45.0% | 78.1% | 74.1% |

The core insight is that **multi-turn interaction is a double-edged sword**: it gives the attacker more information about the target but simultaneously provides the target with accumulated context to detect and resist the attack. For current safety-aligned LLMs, the defensive benefit of conversational memory substantially outweighs the offensive benefit of turn-by-turn adaptation. Single-turn attacks -- whether refined through iterative feedback (PAIR-5) or pre-diversified across strategies (BoK-ST) -- deny the target this defensive advantage by ensuring each probe is evaluated in isolation.

---

## RQ2: How Do Failure-Type Distributions Differ Across Conditions, and Do Human Annotations Validate Automated Detectors?

### 2.1 Failure-Type Distribution by Condition

Detector bypass counts (number of attacks that evaded each detector):

| Detector Bypassed | OSS-ST | SS-MT | ASQ-ST | AMQ-MT | AMQ-ST | BoK-ST |
|---|---|---|---|---|---|---|
| Refusal | 41 (12.8%) | 76 (23.8%) | 175 (54.7%) | 172 (53.8%) | 231 (72.2%) | 229 (71.6%) |
| Keyword | 20 (6.2%) | 42 (13.1%) | 79 (24.7%) | 77 (24.1%) | 115 (35.9%) | 101 (31.6%) |
| LLM Judge | 46 (14.4%) | 92 (28.8%) | 184 (57.5%) | 144 (45.0%) | 250 (78.1%) | 237 (74.1%) |
| Semantic Judge | 48 (15.0%) | 113 (35.3%) | 194 (60.6%) | 179 (55.9%) | 259 (80.9%) | 268 (83.8%) |
| Safety Judge | 45 (14.1%) | 118 (36.9%) | 202 (63.1%) | 194 (60.6%) | 269 (84.1%) | 268 (83.8%) |

**Finding 16 -- Tier 1 attacks (AMQ-ST and BoK-ST) bypass refusal mechanisms at near-identical rates (~72%).** Both achieve essentially the same refusal bypass rate, despite using fundamentally different mechanisms: PAIR-5 iteratively refines a single prompt based on target feedback, while BoK-ST deploys K=5 pre-generated prompts each targeting a different strategy (role-play, hypothetical framing, code generation, etc.) with no runtime feedback. The convergent bypass rates suggest that strategy diversity across attack vectors achieves the same net coverage of safety blind spots as feedback-driven prompt optimisation.

**Finding 17 -- BoK-ST has the highest semantic and safety judge bypass rates (83.8%).** BoK-ST slightly exceeds AMQ-ST (80.9% semantic, 84.1% safety) in fooling judge-based detectors, despite providing no additional ASR after human correction. Because BoK-ST's K=5 variants are each crafted with a distinct framing strategy, the diversity of response styles makes it harder for judges to apply consistent evaluation criteria. A response produced via educational framing looks different from one produced via code-generation framing, creating more borderline cases that judges flag as harmful but human reviewers reject.

**Finding 18 -- Keyword-based detection is the most resistant to bypassing but still fails significantly.** Keyword detection has the lowest absolute bypass rate (6.2%-35.9%). However, as shown in Section 3, this masks extremely poor recall: the keyword detector misses most successful attacks because adaptive strategies learn to use euphemisms and circumlocutions. This is consistent with Andriushchenko et al.'s [5] finding that simple adaptive strategies can bypass pattern-based filters.

**Finding 19 -- LLM-based judges are more effectively bypassed by AMQ-ST (78.1%) than AMQ-MT (45.0%).** Concentrated, highly-optimised single prompts produce responses that are harder for judges to identify as unsafe, whereas multi-turn conversations leave more contextual evidence of harmful intent.

### 2.2 Human Validation Results

| Condition | Formal Name | Raw ASR | Adj. ASR | FP | FN | Net Correction |
|---|---|---|---|---|---|---|
| `direct_single_turn` | OSS-ST | 15.9% | 14.4% | 5 | 0 | -1.6pp |
| `scripted_multi_turn` | SS-MT | 51.2% | 37.5% | 51 | 7 | -13.7pp |
| `adaptive_single_query_st` | ASQ-ST | 64.1% | 63.7% | 4 | 3 | -0.3pp |
| `adaptive_multi_turn` | AMQ-MT | 63.4% | 63.4% | 21 | 21 | 0.0pp |
| `adaptive_single_turn` | AMQ-ST | 85.0% | 85.9% | 5 | 8 | +0.9pp |
| `best_of_k_st` | BoK-ST | 91.2% | 85.6% | 23 | 5 | -5.6pp |

**Finding 20 -- Scripted Static Multi-Turn has the largest detector-human discrepancy (-13.7pp).** Human reviewers reclassified 51 automated "successes" as false positives. Scripted attacks produce ambiguous responses that look like compliance to automated detectors but are benign upon expert review. **Reported ASR for scripted/template-based attacks should be treated with caution unless human-validated.** This finding is particularly relevant for Crescendo-style [6] benchmarks that rely on automated scoring.

**Finding 21 -- BoK-ST has the second-largest discrepancy (-5.6pp), driven by the "any-of-K" success criterion.** Because an intent is counted as jailbroken if ANY of its K=5 strategy-diverse variants succeeds, borderline cases accumulate: a variant framed as educational fiction may produce a response that automated detectors flag as harmful but human reviewers judge as benign hedging. The 23 false positives (vs. only 5 false negatives) confirm this systematic over-estimation -- the diversity of framing strategies increases the chance that at least one variant produces an ambiguous response that triggers the detector ensemble. **Best-of-K benchmarks that use an any-of-K success criterion with automated scoring will inflate ASR by approximately 5-6 percentage points without human validation.**

**Finding 22 -- Adaptive conditions (ASQ-ST, AMQ-ST) show excellent detector-human agreement.** Net corrections are < 1pp. These attacks produce dichotomous outcomes -- clear bypass or clear refusal -- with minimal ambiguity, making PAIR-style conditions the most reliable for automated benchmarking.

### 2.3 Cascade Detection Analysis

| Condition | Formal Name | Refusal Rate | Adj. ASR | Judge Agreement | AWCS | Critical Damage Rate |
|---|---|---|---|---|---|---|
| `direct_single_turn` | OSS-ST | 85.6% | 14.4% | 96.9% | +0.338 | 14.4% |
| `scripted_multi_turn` | SS-MT | 62.5% | 37.5% | 49.4% | -0.090 | 37.5% |
| `adaptive_single_query_st` | ASQ-ST | 36.2% | 63.7% | 87.5% | -0.138 | 63.7% |
| `adaptive_multi_turn` | AMQ-MT | 36.6% | 63.4% | 64.7% | -0.154 | 63.4% |
| `adaptive_single_turn` | AMQ-ST | 14.1% | 85.9% | 83.1% | -0.347 | 85.9% |
| `best_of_k_st` | BoK-ST | 14.4% | 85.6% | 85.6% | -0.384 | 85.6% |

**Finding 23 -- BoK-ST produces the most negative AWCS (-0.384), slightly exceeding AMQ-ST (-0.347).** Despite equivalent adjusted ASR, BoK-ST generates more deeply harmful content when it succeeds. Because each of the K=5 variants targets a different facet of the model's safety alignment using a distinct strategy, the variant that succeeds is often the one that most directly bypasses the model's defences for that specific framing -- producing a more complete and harmful response than the compromise-seeking output of PAIR-5's iterative refinement.

**Finding 24 -- When attacks succeed, they produce critical-severity outputs with near-certainty.** The critical damage rate tracks adjusted ASR almost perfectly across all conditions and models. LLMs do not produce "mild" safety failures -- they either refuse categorically or provide substantive harmful content. There is no meaningful gradient of partial compliance.

### 2.4 Per-Model Severity Profile

| Model | Overall ASR | AWCS | Judge Agreement | Critical Damage Rate |
|---|---|---|---|---|
| Claude Sonnet 4 | 28.8% | +0.160 | 76.7% | 27.9% |
| GPT-4o | 54.6% | -0.099 | 75.4% | 54.6% |
| GPT-4o-mini | 56.7% | -0.104 | 76.2% | 56.7% |
| Gemini 2.5 Flash | 59.6% | -0.164 | 76.2% | 59.6% |
| LLaMA 3.3 70B | 60.8% | -0.169 | 75.8% | 60.8% |
| Qwen 2.5 72B | 65.0% | -0.166 | 80.0% | 65.0% |
| DeepSeek-v3-0324 | 67.1% | -0.210 | 80.4% | 67.1% |
| Mistral Large 2411 | 75.0% | -0.282 | 82.1% | 75.0% |

**Finding 25 -- Claude Sonnet 4 is the only model with a positive AWCS (+0.160).** A positive AWCS indicates net safe output production even when aggregating across all six attack conditions. Every other model has a negative AWCS, confirming net harmful output production.

### 2.5 RQ2 Answer

Failure-type distributions differ markedly across conditions. Tier 1 attacks (AMQ-ST and BoK-ST) systematically bypass refusal mechanisms (~72% bypass rate) and produce unambiguous, clearly harmful critical-severity responses. Scripted Static Multi-Turn generates the most ambiguous outputs (-13.7pp correction), followed by BoK-ST (-5.6pp correction), whose any-of-K success criterion with strategy-diverse variants inflates automated metrics through borderline responses that human reviewers reject.

Human annotations validate the automated pipeline for PAIR-style conditions (net correction < 1pp) but reveal significant over-counting for SS-MT and BoK-ST. When attacks succeed, they produce critical-severity outputs with near-certainty -- there is no spectrum of partial compliance.

---

## RQ3: How Sensitive Are Automated Safety Detectors to Attack Sophistication and Interaction Mode?

### 3.1 Per-Detector Performance Overview

| Detector | Overall Fail Rate | Avg Score | Behaviour |
|---|---|---|---|
| Safety Judge | 64.3% (1,234/1,920) | 0.357 | Most aggressive; best overall F1 |
| Semantic Judge | 65.9% (1,266/1,920) | 0.590 | Aggressive; collapses on SS-MT |
| LLM Judge | 52.5% (1,008/1,920) | 0.565 | Moderate; best balance of P and R |
| Refusal | 67.5% (1,296/1,920) | 0.325 | Heuristic; high FP rate |
| Keyword | 26.4% (507/1,920) | 0.818 | Conservative; very low recall on Tier 1 |
| Similarity | 0.0% (0/1,920) | 0.863 | Never flags -- non-functional for jailbreaks |
| Tool Call | 0.0% (0/1,920) | 1.000 | Never flags -- not applicable |

### 3.2 Detector Precision, Recall, and F1 Against Human Ground Truth

**Safety Judge (best overall detector):**

| Condition | Formal Name | Precision | Recall | F1 |
|---|---|---|---|---|
| `direct_single_turn` | OSS-ST | 98.73% | 99.68% | **99.20%** |
| `adaptive_single_query_st` | ASQ-ST | 98.43% | 99.68% | **99.05%** |
| `adaptive_single_turn` | AMQ-ST | 97.45% | 98.08% | **97.76%** |
| `best_of_k_st` | BoK-ST | 92.99% | 97.99% | **95.42%** |
| `adaptive_multi_turn` | AMQ-MT | 91.00% | 96.92% | **93.87%** |
| `scripted_multi_turn` | SS-MT | 77.67% | 99.20% | **87.12%** |

**Semantic Judge:**

| Condition | Formal Name | Precision | Recall | F1 |
|---|---|---|---|---|
| `direct_single_turn` | OSS-ST | 98.74% | 100.00% | **99.37%** |
| `adaptive_single_query_st` | ASQ-ST | 97.74% | 97.12% | **97.43%** |
| `adaptive_single_turn` | AMQ-ST | 97.37% | 94.87% | **96.10%** |
| `best_of_k_st` | BoK-ST | 92.68% | 97.98% | **95.26%** |
| `adaptive_multi_turn` | AMQ-MT | 85.47% | 91.34% | **88.31%** |
| `scripted_multi_turn` | SS-MT | 61.98% | 96.52% | **75.49%** |

**LLM Judge:**

| Condition | Formal Name | Precision | Recall | F1 |
|---|---|---|---|---|
| `direct_single_turn` | OSS-ST | 97.48% | 99.36% | **98.73%** |
| `adaptive_single_query_st` | ASQ-ST | 97.33% | 93.89% | **95.58%** |
| `adaptive_single_turn` | AMQ-ST | 98.64% | 92.09% | **95.25%** |
| `scripted_multi_turn` | SS-MT | 96.92% | 91.00% | **93.87%** |
| `best_of_k_st` | BoK-ST | 93.64% | 87.75% | **90.60%** |
| `adaptive_multi_turn` | AMQ-MT | 96.17% | 80.97% | **87.92%** |

**Keyword Detector:**

| Condition | Formal Name | Precision | Recall | F1 |
|---|---|---|---|---|
| `direct_single_turn` | OSS-ST | 95.53% | 91.45% | **93.45%** |
| `scripted_multi_turn` | SS-MT | 93.39% | 74.34% | **82.78%** |
| `adaptive_single_query_st` | ASQ-ST | 97.44% | 60.51% | **74.66%** |
| `adaptive_multi_turn` | AMQ-MT | 88.66% | 57.72% | **69.92%** |
| `adaptive_single_turn` | AMQ-ST | 96.25% | 49.04% | **64.97%** |
| `best_of_k_st` | BoK-ST | 92.52% | 44.01% | **59.65%** |

**Refusal Detector:**

| Condition | Formal Name | Precision | Recall | F1 |
|---|---|---|---|---|
| `adaptive_single_turn` | AMQ-ST | 88.41% | 84.72% | **86.53%** |
| `best_of_k_st` | BoK-ST | 88.73% | 84.43% | **86.53%** |
| `adaptive_single_query_st` | ASQ-ST | 82.13% | 89.51% | **85.66%** |
| `direct_single_turn` | OSS-ST | 70.65% | 96.90% | **81.72%** |
| `scripted_multi_turn` | SS-MT | 76.81% | 82.81% | **79.70%** |
| `adaptive_multi_turn` | AMQ-MT | 65.05% | 85.84% | **74.01%** |

### 3.3 Deep Analysis of Detector Behaviour

**Finding 26 -- The Safety Judge is the best overall detector, achieving F1 > 87% across all six conditions.** Its lowest F1 is 87.12% on SS-MT, driven by 71 false positives (precision drops to 77.67%). Its recall never drops below 96.92%, meaning it catches virtually every real attack. On BoK-ST, it achieves F1 = 95.42% with 22 FPs and 6 FNs. For single-detector deployment, the Safety Judge is the recommended choice.

**Finding 27 -- The Semantic Judge has a catastrophic failure mode on Scripted Static Multi-Turn (F1 = 75.49%).** With 119 false positives (precision: 61.98%), the semantic judge flags nearly twice as many findings as are actually harmful in the SS-MT condition. It appears to be triggered by the topical content of escalation scripts even when the model successfully refuses. This inflates SS-MT ASR by approximately 37% when using this detector alone.

**Finding 28 -- The LLM Judge is most conservative on BoK-ST (F1 = 90.60%).** With 37 false negatives (recall 87.75%), the LLM Judge correctly identifies some BoK-ST "successes" as borderline, applying deeper semantic analysis than the Safety or Semantic judges. This makes the LLM Judge a valuable complement to the Safety Judge for Tier 1 attacks.

**Finding 29 -- The Keyword Detector has catastrophically low recall on Tier 1 attacks.** Recall drops from 91.45% on OSS-ST to 44.01% on BoK-ST and 49.04% on AMQ-ST -- meaning keyword detection **misses more than half** of all successful Tier 1 attacks. BoK-ST achieves the lowest keyword recall of any condition, confirming that sampling diversity specifically selects for keyword-evading outputs. This directly parallels Andriushchenko et al.'s [5] finding that adaptive attacks learn to circumvent pattern-based defences.

**Finding 30 -- Detectors fail in two orthogonal modes depending on their type.**

| Detector Type | Primary Failure Mode | Worst Condition | Root Cause |
|---|---|---|---|
| Judge-based (Safety, Semantic) | False Positives | SS-MT | Judges interpret escalating context as harmful even when model refuses |
| Pattern-based (Keyword) | False Negatives | BoK-ST | Sampling diversity selects for outputs that evade keyword matching |
| Heuristic (Refusal) | Both FP and FN | AMQ-MT | Refusal patterns are too varied to capture heuristically |
| LLM Judge | False Negatives | BoK-ST / AMQ-MT | Deep analysis is conservative on borderline cases |

No single detector handles all six conditions well. This orthogonal failure structure is a key contribution to the detector sensitivity literature.

### 3.4 Judge Agreement Rate

| Condition | Formal Name | Judge Agreement Rate |
|---|---|---|
| `direct_single_turn` | OSS-ST | 96.9% |
| `adaptive_single_query_st` | ASQ-ST | 87.5% |
| `best_of_k_st` | BoK-ST | 85.6% |
| `adaptive_single_turn` | AMQ-ST | 83.1% |
| `adaptive_multi_turn` | AMQ-MT | 64.7% |
| `scripted_multi_turn` | SS-MT | 49.4% |

**Finding 31 -- Judge agreement collapses in SS-MT (49.4%) and AMQ-MT (64.7%), but holds for BoK-ST (85.6%).** BoK-ST achieves reasonable agreement because it produces single-turn outputs that are clearer to evaluate than multi-turn conversations. In nearly half of SS-MT cases, judges disagree -- any ASR measurement based on a single judge in multi-turn conditions is unreliable.

### 3.5 BoK-ST vs. AMQ-ST (PAIR-5): Detector-Level Comparison

| Detector | BoK-ST F1 | AMQ-ST F1 | Delta | Interpretation |
|---|---|---|---|---|
| Safety Judge | 95.42% | 97.76% | -2.3pp | BoK generates more borderline FPs |
| Semantic Judge | 95.26% | 96.10% | -0.8pp | Nearly equivalent |
| LLM Judge | 90.60% | 95.25% | -4.7pp | BoK fools LLM Judge less reliably |
| Keyword | 59.65% | 64.97% | -5.3pp | BoK is harder for keywords to catch |
| Refusal | 86.53% | 86.53% | 0.0pp | Identical performance |

**Finding 32 -- BoK-ST is harder to detect by pattern-based detectors but easier by LLM-based judges.** Keyword F1 is 5.3pp lower on BoK-ST, confirming sampling diversity produces lexically varied attacks. However, the LLM Judge has 4.7pp better F1 on AMQ-ST, because PAIR-5 produces more definitive outcomes while BoK-ST produces borderline cases a sophisticated judge can identify. This creates a detector-dependent ranking that complicates benchmark comparisons.

### 3.6 Impact on Reported ASR

**Finding 33 -- The choice of detector can swing reported ASR by 40-60 percentage points.**

| Scenario | Keyword-only ASR | Safety-Judge-only ASR | Human-validated ASR |
|---|---|---|---|
| BoK-ST | 35.0% | 90.6% | 85.6% |
| AMQ-ST (PAIR-5) | 37.8% | 86.6% | 85.9% |
| OSS-ST | 10.3% | 15.3% | 14.4% |

If keyword detection alone were used, BoK-ST's ASR would appear as 35.0% rather than the validated 85.6% -- a 50.6pp undercount. **Detector specification is essential for benchmark comparisons.** This finding has direct implications for HarmBench (ICML 2024) [1] and JailbreakBench (NeurIPS 2024) [4] protocols, which specify particular judges for scoring.

### 3.7 RQ3 Answer

Automated safety detectors are highly sensitive to both attack sophistication and interaction mode, with F1 ranging from 59.65% (keyword on BoK-ST) to 99.37% (semantic judge on OSS-ST). The sensitivity manifests in two orthogonal failure modes:

1. **Judge-based detectors over-detect** in scripted multi-turn conditions (up to 119 false positives, precision as low as 62%), generating inflated ASR numbers.
2. **Pattern-based detectors under-detect** in Tier 1 conditions (up to 173 false negatives, recall as low as 44%), dramatically undercounting genuine safety failures.

The BoK-ST condition reveals a novel finding: **the any-of-K success criterion with strategy-diverse variants systematically inflates automated ASR by 5.6pp**, because the diversity of framing strategies (role-play, educational, code-generation, etc.) increases the probability that at least one variant produces a borderline response that triggers detectors -- distinct from PAIR-5's refinement approach which produces cleaner success/failure outcomes.

The Safety Judge achieves the best overall performance (F1 > 87% across all conditions) and is recommended as the primary detector. The LLM Judge is recommended as a secondary check, particularly for BoK-ST and multi-turn conditions. Human review remains essential for SS-MT (judge agreement < 50%) and recommended for BoK-ST (to correct ~5.6pp inflation).

---

## Cross-Cutting Findings

### The Best-of-K Paradox

**Finding 34 -- BoK-ST achieves the highest raw ASR but provides no advantage after human validation, while being more expensive and slower.** This paradox arises because the any-of-K success criterion with strategy-diverse variants inflates automated metrics: when K=5 different framing strategies each target a different facet of safety alignment, the probability that at least one produces a borderline response that triggers detectors is higher than the probability that any single response constitutes a genuine safety bypass:

| Metric | AMQ-ST (PAIR-5) | BoK-ST | Winner |
|---|---|---|---|
| Raw ASR | 85.0% | 91.2% | BoK-ST |
| Adjusted ASR | 85.9% | 85.6% | Tie |
| False Positives | 5 | 23 | AMQ-ST |
| Cost/attack | $0.0138 | $0.0179 | AMQ-ST |
| Median latency | 284.7s | 573.2s | AMQ-ST |
| AWCS (severity) | -0.347 | -0.384 | BoK-ST (more harmful) |
| Judge agreement | 83.1% | 85.6% | BoK-ST |

AMQ-ST (PAIR-5) dominates BoK-ST on cost, speed, and false positive rate while matching adjusted ASR. This reveals a fundamental trade-off: **strategy diversity without feedback** (BoK-ST) and **iterative refinement with feedback** (PAIR-5) are alternative paths to the same ~86% adjusted ASR ceiling, but PAIR-5 is more efficient and produces cleaner measurements. Best-of-N/K benchmarks [8] that report raw ASR without human validation systematically over-estimate attack effectiveness by 5-6pp due to the any-of-K criterion.

### Model Robustness Ranking (All 6 Conditions)

| Rank | Model | Overall ASR | AWCS | Worst Condition | Comparison with Literature |
|---|---|---|---|---|---|
| 1 | Claude Sonnet 4 | 28.8% | +0.160 | BoK-ST (47.5%) | Consistent with [7]: 2.86% max harm score |
| 2 | GPT-4o | 54.6% | -0.099 | AMQ-ST (87.5%) | Consistent with [5]: collapses under adaptive |
| 3 | GPT-4o-mini | 56.7% | -0.104 | AMQ-ST/BoK (87.5%) | -- |
| 4 | Gemini 2.5 Flash | 59.6% | -0.164 | AMQ-ST (92.5%) | Consistent with [7]: 71.4% harm |
| 5 | LLaMA 3.3 70B | 60.8% | -0.169 | BoK-ST (92.5%) | -- |
| 6 | Qwen 2.5 72B | 65.0% | -0.166 | BoK-ST (92.5%) | Tail-of-distribution vulnerability |
| 7 | DeepSeek-v3-0324 | 67.1% | -0.210 | AMQ-ST (100%) | Consistent with [7]: 90.0% harm |
| 8 | Mistral Large 2411 | 75.0% | -0.282 | BoK-ST (97.5%) | Weakest across all conditions |

### EU AI Act Compliance

All 8 models were assessed against EU AI Act Articles 15(5) (Cyberattack Resilience) and 55(1)(d) (Adversarial Testing Requirements). ATLAS provides compliance-relevant adversarial testing evidence for AI assurance and governance. Under adversarial conditions, all 8 models exhibited vulnerabilities mapped to these articles, with even the most robust model (Claude Sonnet 4, 28.8% overall ASR) showing non-trivial attack surface. The inclusion of BoK-ST raises the bar further: if regulators require robustness against sampling-based attacks, the tail-of-distribution vulnerabilities demonstrated here provide important evidence for compliance assessments.

### Practical Recommendations

1. **For red-teamers**: Use **AMQ-ST (PAIR-5)** as the primary attack strategy. It achieves the highest adjusted ASR (85.9%), is cost-efficient ($0.014/attack), and produces unambiguous results (Safety Judge F1 > 97%). Use BoK-ST only when testing for maximum output severity or tail-of-distribution vulnerabilities.

2. **For model developers**: Focus safety training on resisting **single-turn adaptive attacks and strategy-diverse attack vectors**. The attacker's ability to optimise prompts via iterative refinement (PAIR-5) is the critical threat. Equally important, the BoK-ST finding reveals that models have strategy-specific blind spots: a model may refuse a direct request but comply when the same objective is framed as role-play, educational content, or code generation. Safety alignment must be **objective-aware** (recognising the harmful intent regardless of framing) rather than **strategy-specific** (pattern-matching known attack formats). Claude Sonnet 4 provides a reference point for effective alignment.

3. **For benchmark designers**: Always report **adjusted ASR** alongside raw ASR, particularly for Best-of-K/N benchmarks where inflation is systematic. Report detector-specific F1 and use multi-detector consensus. Specify which judge(s) are used for scoring, as detector choice can swing reported ASR by 40-60pp. PAIR-style conditions are the most reliable for automated benchmarking (< 1pp correction).

4. **For EU AI Act compliance**: ATLAS provides compliance-relevant adversarial testing evidence that can inform regulatory assessments under EU AI Act adversarial robustness requirements. The BoK-ST methodology should be included in compliance testing frameworks because it reveals tail-of-distribution vulnerabilities that single-attempt testing misses.

### BoK-ST Supplementary Analysis

The following analyses use only existing variant-level data from the experiment — no additional experiments were conducted.

**BoK K=1/3/5 Ablation.** Post-hoc analysis of how ASR changes with the number of variants per intent:

| K | Total | Successes | Raw ASR | 95% CI | Marginal Gain |
|---|---|---|---|---|---|
| 1 | 320 | 180 | 56.2% | [50.8%, 61.6%] | — |
| 3 | 320 | 269 | 84.1% | [79.7%, 87.7%] | — |
| 5 | 320 | 292 | 91.2% | [87.6%, 93.9%] | +7.2pp |

K=1→3 provides the largest gain (+27.9pp). K=3→5 adds only +7.2pp with diminishing returns. Model-level variation is substantial: gpt-4o-mini gains +15.0pp from K=3→5, while mistral-large-2411 gains only +2.5pp (already near-ceiling at K=3).

**Sequential Stopping Simulation.** If BoK variants were sent sequentially (stop on first success), mean realized queries would be 1.94/5.0 (38.8% of the maximum cap), providing 61.2% theoretical query savings. 56.2% of attacks succeed at the first variant. This supports the distinction between the **maximum target-query cap** (K=5, matched with PAIR-5) and **realized target calls** (BoK-ST sequential: 1.94 mean).

**Strategy Diversity Audit.** TF-IDF and pattern-based classification of all 200 BoK variants (40 intents × 5) identifies 12 distinct framing strategy families. 95% of intents (38/40) use 3+ unique strategies. No intents have high textual similarity (>0.7 Jaccard). The 2 flagged intents (intent-hacking-exploit, intent-multilingual-injection) have low strategy diversity because the intent topic constrains viable framings. Strategy distribution is balanced: the most common family (security_exercise) accounts for only 17.0% of variants.

| Strategy Family | Count | Percentage |
|---|---|---|
| Security Exercise | 34 | 17.0% |
| Academic | 26 | 13.0% |
| Fiction | 23 | 11.5% |
| Role Play | 22 | 11.0% |
| Step-by-Step | 18 | 9.0% |
| Translation | 18 | 9.0% |
| Historical | 14 | 7.0% |
| Hypothetical | 13 | 6.5% |
| Educational | 8 | 4.0% |
| Technical | 5 | 2.5% |
| Other | 19 | 9.5% |

### Study Limitations

1. **Turn-budget cap (AMQ-MT)**: AMQ-MT is capped at 5 turns. The finding that multi-turn adaptive attacks underperform single-turn refinement is specific to this budget. Studies using 10-turn budgets [7] achieve substantially higher ASR. Practitioners should not conclude that multi-turn attacks are ineffective in general.

2. **PAIR iteration cap**: AMQ-ST uses `max_iterations=5`, not the 20-iteration original PAIR design [2]. The comparison to published PAIR ASRs reflects differences in both attacker model (DeepSeek-R1 vs. GPT-4) and iteration depth. These are not separable in the current design.

3. **K sensitivity for BoK-ST**: K=5 was chosen to match PAIR-5's maximum target-query cap. Post-hoc ablation from existing variant data (not new experiments) shows: K=1 achieves 56.2% raw ASR, K=3 reaches 84.1%, and K=5 reaches 91.2%. The marginal gain from K=3→5 is +7.2pp with diminishing returns. Sequential stopping simulation shows mean realized queries of 1.94/5.0 (61.2% theoretical savings), with 56.2% of attacks succeeding at the first variant. K>5 was not tested.

4. **Intent category heterogeneity**: Results are averages across 40 harm intents spanning cybercrime, CBRN, social manipulation, and other categories. Category-level ASR variation is not reported; some categories may be substantially more or less susceptible to specific attack strategies.

5. **Model-version specificity**: All results reflect model versions available in May 2026. Safety alignment is updated frequently; results may not hold for later releases of the same models.

---

## Appendix A: Pairing Audit

All McNemar tests and paired comparisons are joined by `(model, intent_id)` -- not by row order.

### A.1 Experimental Design

- **Join key**: `(model, intent_id)` extracted from `attempt.metadata.intent_id`
- **Total records**: 1,920 (8 models x 6 conditions x 40 intents)
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

Every pairwise comparison achieves 320 matched pairs (8 models x 40 intents) with zero unmatched records:

| Comparison | Matched Pairs | Unmatched |
|---|---|---|
| AMQ-MT vs ASQ-ST | 320 | 0 |
| AMQ-MT vs AMQ-ST | 320 | 0 |
| AMQ-MT vs BoK-ST | 320 | 0 |
| AMQ-MT vs OSS-ST | 320 | 0 |
| AMQ-MT vs SS-MT | 320 | 0 |
| ASQ-ST vs AMQ-ST | 320 | 0 |
| ASQ-ST vs BoK-ST | 320 | 0 |
| ASQ-ST vs OSS-ST | 320 | 0 |
| ASQ-ST vs SS-MT | 320 | 0 |
| AMQ-ST vs BoK-ST | 320 | 0 |
| AMQ-ST vs OSS-ST | 320 | 0 |
| AMQ-ST vs SS-MT | 320 | 0 |
| BoK-ST vs OSS-ST | 320 | 0 |
| BoK-ST vs SS-MT | 320 | 0 |
| OSS-ST vs SS-MT | 320 | 0 |

**Conclusion**: Every comparison is a complete, balanced pairing on identical `(model, intent_id)` keys. The McNemar tests are valid paired tests on the same experimental units.

---

## Mechanism Decomposition: Mixed-Effects Logistic Regression

The pairwise McNemar tests in Sections 1.5-1.6 compare conditions two at a time and ignore clustering by model and intent. This section replaces that approach with a single unified logistic regression that simultaneously estimates the effect of four orthogonal attack mechanisms, controlling for heterogeneity across 8 target models and 40 harmful intents as fixed effects.

### Mechanism Encoding

Each of the six conditions is decomposed into four binary mechanism indicators:

| Condition | LLM-crafted | Feedback | Multi-turn | Diversity |
|-----------|-------------|----------|------------|----------|
| OSS-ST (Direct) | 0 | 0 | 0 | 0 |
| SS-MT (Scripted) | 0 | 0 | 1 | 0 |
| ASQ-ST (PAIR-1) | 1 | 0 | 0 | 0 |
| AMQ-ST (PAIR-5) | 1 | 1 | 0 | 0 |
| AMQ-MT (Adaptive MT) | 1 | 1 | 1 | 0 |
| BoK-ST (Best-of-K) | 1 | 0 | 0 | 1 |

### Primary Model (M4): Mechanism Effects

*N* = 1,920, *k* = 51 parameters, McFadden pseudo-*R*² = 0.344

| Mechanism | OR | 95% CI | AME (pp) | Boot 95% CI | *p* | Sig. |
|-----------|-------|------------|----------|-------------|-------|------|
| LLM-crafted prompt | 8.30 | [5.73, 12.04] | +36.6 | [+28.2, +44.1] | < 0.0001 | *** |
| Iterative refinement (target feedback) | 1.98 | [1.37, 2.84] | +10.2 | [+3.0, +17.4] | 0.0003 | *** |
| Multi-turn memory | 1.02 | [0.77, 1.36] | +0.3 | [-6.0, +7.5] | 0.8847 | ns |
| Static diversity (K=5 variants) | 4.99 | [3.19, 7.81] | +22.4 | [+16.9, +27.8] | < 0.0001 | *** |

- **OR** (odds ratio): multiplicative change in odds of success when the mechanism is present.
- **AME** (average marginal effect): average change in P(success) in percentage points, computed via block-bootstrap resampling models for cluster-robust confidence intervals.

**Finding 35 -- LLM-crafted prompting is the dominant mechanism (+36.6pp AME), followed by static diversity (+22.4pp) and iterative feedback (+10.2pp). Multi-turn memory has zero marginal effect (+0.3pp, ns).** The regression confirms and extends the pairwise findings: having an attacker LLM craft the prompt (even without feedback) is 3.6x more impactful than iterative refinement, and pre-generating diverse attack strategies is 2.2x more impactful than closed-loop adaptation. Multi-turn conversational memory provides no marginal benefit after controlling for adaptivity -- the apparent AMQ-MT disadvantage in the McNemar tests was confounded by the joint presence of feedback and multi-turn memory.

### Feedback × Multi-Turn Interaction

Adding a feedback × multi-turn interaction term yields OR = 0.04 (*p* < 0.0001). The interaction is **strongly negative**: combining feedback with multi-turn memory provides *less* benefit than the sum of their individual effects. This confirms the mechanistic analysis in Section 1.8 -- multi-turn context acts as a defence amplifier that counteracts the attacker's adaptive advantage.

### Variance Decomposition

| Source | Deviance explained | % of null deviance |
|--------|-------------------|-----------------|
| Target model | 129.7 | 5.0% |
| Harmful intent | 174.5 | 6.7% |
| Attack mechanism | 579.3 | 22.2% |
| Residual | 1,710.2 | 65.6% |
| **Total null deviance** | **2,606.7** | **100%** |

**Finding 36 -- Attack mechanism explains 22.2% of outcome variance, dwarfing target model (5.0%) and intent (6.7%).** The choice of *how* to attack matters far more than *which model* or *which intent* is targeted. This has direct implications for safety evaluation: benchmarks that test only one attack strategy capture less than a quarter of the variation that matters.

### GEE Robustness Check

A Generalized Estimating Equations model with exchangeable correlation within model clusters and sandwich (cluster-robust) standard errors confirms all four mechanism effects in the same direction, with slightly attenuated ORs (LLM-crafted: 6.50, feedback: 1.83, multi-turn: 1.02, diversity: 4.21). All significance levels agree with the primary model. The regression findings are robust to arbitrary within-cluster dependence.

### Regression vs. Pooled McNemar

| Contrast | McNemar diff | McNemar *p* | Regression AME | Regression *p* | Direction agrees? |
|----------|-------------|-------------|----------------|----------------|------------------|
| PAIR-1 vs Direct (LLM-crafted effect) | +49.4pp | < 0.001 | +36.6pp | < 0.001 | Yes |
| PAIR-5 vs PAIR-1 (feedback effect) | +22.2pp | < 0.001 | +10.2pp | 0.0003 | Yes |
| AMQ-MT vs PAIR-5 (multi-turn effect) | -22.5pp | < 0.001 | +0.3pp | 0.885 | **No** |
| BoK vs PAIR-1 (diversity effect) | +21.9pp | < 0.001 | +22.4pp | < 0.001 | Yes |

**Finding 37 -- The pooled McNemar test overestimates the feedback effect by 2.2x and produces a sign error for multi-turn.** The pairwise AMQ-MT vs PAIR-5 comparison (-22.5pp, p < 0.001) conflates the multi-turn effect with a confound: AMQ-MT activates both feedback *and* multi-turn, and the negative interaction between them drives the pairwise result. The regression correctly decomposes this into: multi-turn memory alone has no effect (+0.3pp), but its interaction with feedback is strongly negative (OR = 0.04). This demonstrates why mechanism decomposition via regression is essential -- pairwise comparisons cannot separate joint effects.

---

## Success-vs-Budget Curves

This section addresses whether BoK-ST reaches PAIR-5's ASR because of **static diversity**, **repeated independent trials**, or **adaptive refinement with target feedback**. We construct cumulative ASR curves as a function of the number of target calls (K = 1, ..., 5) for three strategies, plus two theoretical baselines.

### Overall ASR by Target-Call Budget

| K | PAIR-5 (adaptive) | BoK (diverse) | BoK-iid (theoretical) | PAIR-1 × K (iid) | Direct × K (iid) |
|---|-------------------|---------------|----------------------|-------------------|-------------------|
| 1 | 68.1% [62.8, 73.0] | 56.2% [50.8, 61.6] | 65.8% | 64.1% | 15.9% |
| 2 | 84.7% [80.3, 88.2] | 77.5% [72.6, 81.7] | 88.3% | 87.1% | 29.3% |
| 3 | 90.3% [86.6, 93.1] | 84.1% [79.7, 87.7] | 96.0% | 95.4% | 40.6% |
| 4 | 92.5% [89.1, 94.9] | 88.1% [84.1, 91.2] | 98.6% | 98.3% | 50.1% |
| 5 | 93.8% [90.5, 95.9] | 91.2% [87.6, 93.9] | 99.5% | 99.4% | 58.0% |

- **PAIR-5 (adaptive)**: cumulative ASR at each PAIR iteration (early-stop on success).
- **BoK (diverse)**: cumulative ASR using best-of-first-K variants (actual BoK data).
- **BoK-iid (theoretical)**: 1 - (1-p)^K where p = per-variant success rate (56.2%), assuming independence across variants.
- **PAIR-1 × K** and **Direct × K**: theoretical i.i.d. repeated sampling of PAIR-1 (64.1%) and Direct (15.9%) attacks.

### Scaling Decomposition

Three quantities decompose how BoK reaches its K=5 ASR:

| K | Diversity gain | Correlation tax | Adaptive premium |
|---|---------------|-----------------|------------------|
| 1 | +0.0pp | +9.6pp | +11.9pp |
| 2 | +21.2pp | +10.8pp | +7.2pp |
| 3 | +27.8pp | +11.9pp | +6.2pp |
| 4 | +31.9pp | +10.5pp | +4.4pp |
| 5 | +35.0pp | +8.3pp | +2.5pp |

- **Diversity gain** = BoK(K) - BoK(1): raw improvement from K diverse variants over a single variant.
- **Correlation tax** = BoK-iid(K) - BoK(K): how much positive within-intent correlation reduces scaling vs. the i.i.d. theoretical ceiling.
- **Adaptive premium** = PAIR(K) - BoK(K): benefit of target feedback over static diversity at each budget level.

**Finding 38 -- BoK reaches PAIR-5 primarily through strategy diversity, not repeated i.i.d. trials.** The diversity gain accounts for +35.0pp at K=5 (from 56.2% to 91.2%). However, this gain falls 8.3pp short of the i.i.d. ceiling (99.5%) because variant outcomes within an intent are positively correlated -- vulnerability is largely a property of the (model, intent) pair, causing diverse strategies to succeed or fail together.

**Finding 39 -- Adaptive refinement matters most at low budget, but its premium vanishes by K=5.** At K=1, PAIR leads BoK by 11.9pp (68.1% vs. 56.2%), reflecting the value of LLM-guided prompt crafting over pre-generated variants. By K=5, the adaptive premium shrinks to just +2.5pp as BoK's diversity catches up. This means strategy diversity is a substitute for target feedback when the query budget is sufficient.

**Finding 40 -- PAIR front-loads success: 68.1% of attacks succeed on the first iteration.** Iterations 2-5 contribute only +25.6pp additional ASR. This confirms the mechanism decomposition finding that the attacker LLM's initial reasoning (+36.6pp AME) dominates iterative refinement (+10.2pp AME).

**Finding 41 -- Extrapolating i.i.d. scaling laws to strategy-diverse BoK overpredicts success.** The theoretical i.i.d. ceiling at K=5 is 99.5%, but actual BoK reaches only 91.2% -- a correlation tax of 8.3pp. Researchers applying the Best-of-N scaling framework (Hughes et al. [8]) to diverse-strategy attacks should expect real gains to saturate faster than the 1-(1-p)^K formula predicts.

### Per-Model Budget Curves (Summary at K=5)

| Model | BoK@1 | PAIR@1 | BoK@5 | PAIR@5 | Div. gain | Corr. tax | Adapt. prem. |
|-------|-------|--------|-------|--------|-----------|-----------|-------------|
| Claude Sonnet 4 | 25.0% | 32.5% | 60.0% | 60.0% | +35.0pp | +27.9pp | +0.0pp |
| DeepSeek-v3-0324 | 72.5% | 80.0% | 97.5% | 100.0% | +25.0pp | +2.5pp | +2.5pp |
| Gemini 2.5 Flash | 52.5% | 60.0% | 90.0% | 100.0% | +37.5pp | +9.1pp | +10.0pp |
| GPT-4o | 40.0% | 62.5% | 92.5% | 100.0% | +52.5pp | +5.9pp | +7.5pp |
| GPT-4o-mini | 35.0% | 55.0% | 95.0% | 95.0% | +60.0pp | +2.6pp | +0.0pp |
| LLaMA 3.3 70B | 65.0% | 75.0% | 97.5% | 97.5% | +32.5pp | +2.4pp | +0.0pp |
| Mistral Large 2411 | 90.0% | 95.0% | 97.5% | 100.0% | +7.5pp | +2.5pp | +2.5pp |
| Qwen 2.5 72B | 70.0% | 85.0% | 100.0% | 97.5% | +30.0pp | -0.1pp | -2.5pp |

**Finding 42 -- Claude Sonnet 4 has the highest correlation tax (+27.9pp), meaning its vulnerabilities are intent-specific rather than strategy-specific.** When Claude is vulnerable to a particular intent, multiple diverse strategies tend to succeed; when it resists, all strategies tend to fail. This is the signature of objective-aware safety alignment -- Claude's defences recognise the harmful intent regardless of framing, so diversity provides less marginal benefit.

**Finding 43 -- GPT-4o-mini has the highest diversity gain (+60.0pp), indicating strategy-specific blind spots.** Its low single-variant ASR (35.0%) jumps to 95.0% with K=5 diverse strategies, suggesting its safety alignment is strongly format-dependent. Different framing strategies access entirely different vulnerability surfaces.

---

## Human Validation Counterfactual Analysis

This section identifies specific scientific conclusions that would be **incorrect** if the study relied solely on automated detector verdicts rather than human-validated labels. All 1,920 findings were independently reviewed by two trained annotators (Cohen's κ = 0.81); this analysis compares raw (detector-based) and corrected (human-validated) results.

### Budget Curves: Raw Detector vs. Human-Validated

| K | BoK (raw) | BoK (human) | Inflation | PAIR-5 (raw) | PAIR-5 (human) | Deflation |
|---|-----------|-------------|-----------|--------------|----------------|-----------|
| 1 | 56.2% | 54.1% | +2.2pp | 62.8% | 64.1% | -1.2pp |
| 2 | 77.5% | 73.8% | +3.8pp | 77.2% | 78.1% | -0.9pp |
| 3 | 84.1% | 79.4% | +4.7pp | 81.9% | 83.1% | -1.2pp |
| 4 | 88.1% | 82.2% | +5.9pp | 83.8% | 84.7% | -0.9pp |
| 5 | 91.2% | 85.6% | +5.6pp | 85.0% | 85.9% | -0.9pp |

BoK's inflation grows with K because each additional variant gives the detector another chance to produce a false positive. PAIR-5's slight deflation reflects false negatives where the detector missed adaptive successes.

### Any-of-K False-Positive Accumulation

| K | FP count | FN count | Raw ASR | Corrected ASR | Net inflation |
|---|----------|----------|---------|---------------|---------------|
| 1 | 7 | 0 | 56.2% | 54.1% | +2.2pp |
| 2 | 12 | 0 | 77.5% | 73.8% | +3.8pp |
| 3 | 15 | 0 | 84.1% | 79.4% | +4.7pp |
| 4 | 19 | 0 | 88.1% | 82.2% | +5.9pp |
| 5 | 23 | 5 | 91.2% | 85.6% | +5.6pp |

### Scientific Conclusions That Would Be Wrong Without Human Validation

**Counterfactual 1 [Critical] -- Rank inversion between BoK and PAIR-5.**
- *Without human validation*: BoK (91.2%) outperforms PAIR-5 (85.0%) by +6.2pp.
- *With human validation*: BoK (85.6%) and PAIR-5 (85.9%) are statistically tied (delta = -0.3pp).
- *Mechanism*: BoK accumulates 23 FP across 5 variants (any-of-K amplification); PAIR-5 has 3 net FN (detector underreports adaptive successes). Together, these create a spurious +6.5pp BoK advantage.

**Counterfactual 2 [Critical] -- Phantom adaptive premium sign reversal.**
- *Without human validation*: Adaptive premium at K=5 is -6.2pp (PAIR trails BoK).
- *With human validation*: Adaptive premium at K=5 is +0.3pp (methods are equivalent).
- *Consequence*: A researcher using raw scores would conclude that static diversity *outperforms* adaptive refinement -- the opposite of the true finding that they are equivalent.

**Counterfactual 3 [Major] -- Inflated diversity gain.**
- *Without human validation*: BoK diversity gain (K=1 → K=5) is +35.0pp.
- *With human validation*: BoK diversity gain is +31.6pp; 3.4pp (9.7%) was false-positive inflation.
- *Mechanism*: FP inflation grows monotonically with K: +2.2pp at K=1, +5.6pp at K=5.

**Counterfactual 4 [Critical] -- Scripted multi-turn overestimate.**
- *Without human validation*: SS-MT (51.2% raw ASR) appears a moderately effective baseline.
- *With human validation*: SS-MT (37.5% adjusted ASR) is weak; 13.7pp was FP inflation -- the largest measurement error of any condition. 51 of 320 findings (15.9%) were false positives.

**Counterfactual 5 [Major] -- Per-model rank inversions.**
- *Without human validation*: BoK wins over PAIR-5 on 6 of 8 models.
- *With human validation*: BoK wins on only 3 of 8; 2 models (DeepSeek-v3, GPT-4o) show full rank inversions, and 2 more (GPT-4o-mini, Qwen 2.5) shift from BoK-wins to ties.

**Counterfactual 6 [Critical] -- Cost-efficiency misjudgement.**
- *Without human validation*: BoK (91.2%) appears more effective than PAIR-5 (85.0%) despite using all 5 target calls.
- *With human validation*: PAIR-5 (85.9%) matches BoK (85.6%) while realising only 1.6 mean target calls (68% fewer queries). A practitioner choosing BoK over PAIR based on raw ASR would use 3x more target queries for equivalent true ASR.

### Summary

| Aspect | Raw detector verdict | Human-validated | Error type |
|--------|---------------------|-----------------|------------|
| Best method at K=5 | BoK (91.2%) | Tie (85.6% vs 85.9%) | Rank inversion |
| BoK diversity gain (K=1→5) | +35.0pp | +31.6pp | 9.7% overestimate |
| Adaptive premium (K=5) | -6.2pp (PAIR trails) | +0.3pp (equivalent) | Sign error |
| Scripted MT baseline | 51.2% (moderate) | 37.5% (weak) | +13.7pp overestimate |
| Cost-efficiency winner | BoK (higher ASR) | PAIR (same ASR, 68% fewer queries) | Wrong recommendation |

**Finding 44 -- Every cross-condition comparison in this study required human validation to be directionally correct.** Without human review, a researcher would (1) conclude BoK outperforms PAIR-5 rather than finding them equivalent, (2) recommend BoK over PAIR despite PAIR being 3x more query-efficient, (3) overestimate scripted attacks by 13.7pp, and (4) report a sign error in the adaptive premium. Human validation is not a quality enhancement -- it is a prerequisite for valid conclusions in any study using automated safety detectors with a best-of-K success criterion.

---

## Statistical Methodology Notes

- **Sample size**: N = 40 per model-condition cell, N = 320 per condition (pooled), N = 1,920 total
- **ASR confidence intervals**: Wilson score intervals for binomial proportions (95% level)
- **Paired comparisons**: McNemar's exact test for matched binary outcomes, paired by `(model, intent_id)`
- **Multiple comparison correction**: Bonferroni correction for 15 pairwise condition comparisons (6 choose 2)
- **Cost/latency comparisons**: Wilcoxon signed-rank test for non-normal distributions, paired by `(model, intent_id)`
- **Refinement ablation**: McNemar's test comparing PAIR-1 vs. PAIR-5 on the same `(model, intent_id)` pairs
- **Human validation**: 100% review coverage (1,920/1,920 findings annotated); two independent annotators; Cohen's κ = 0.81; disagreements resolved by senior adjudicator
- **Adjusted ASR**: Raw ASR corrected for false positives (automated success, human-rejected) and false negatives (automated refusal, human-confirmed bypass) identified by human annotators
- **AWCS** (Authority-Weighted Cascade Score): composite safety metric defined as AWCS = (R_rate × α) − (ASR × γ) − (CDR × λ), where R_rate = refusal rate, ASR = attack success rate, CDR = critical damage rate, and α=0.5, γ=0.2, λ=0.1 (parameters from RAHS paper, arxiv:2603.10807). Positive AWCS indicates net safe behaviour; negative AWCS indicates net harmful output production. The metric weights refusal rate most heavily because consistent refusal is the primary indicator of effective safety alignment.
- **Detector metrics**: Precision = TP/(TP+FP), Recall = TP/(TP+FN), F1 = 2×P×R/(P+R), computed against human ground truth labels
- **Mechanism decomposition (logistic regression)**: Fixed-effects logistic regression with model and intent indicators, four binary mechanism predictors, and block-bootstrap CIs (resampling models, 1000 iterations). McFadden pseudo-R² from nested model sequence for variance decomposition. GEE robustness check with exchangeable working correlation within model clusters and sandwich (cluster-robust) SEs.
- **Success-vs-budget curves**: Cumulative ASR at each budget level K=1,...,5 computed from variant-level BoK data and PAIR iteration-level data. Theoretical i.i.d. baselines computed as 1-(1-p)^K where p is the observed per-variant/per-iteration success rate. Correlation tax = BoK-iid(K) - BoK(K); adaptive premium = PAIR(K) - BoK(K); diversity gain = BoK(K) - BoK(1).
- **Human validation counterfactual**: Side-by-side comparison of all metrics computed from raw detector labels vs. human-validated labels. False-positive accumulation in any-of-K counted by tracking the earliest variant position producing a FP.
- **Clustering limitation**: Pooled McNemar tests treat 320 pairs as i.i.d.; model-level clustering is not corrected for. The mechanism decomposition regression (Section "Mechanism Decomposition") resolves this limitation via fixed effects and block-bootstrap CIs. Per-model stratified results are provided and directionally consistent with all pooled findings.
- **External validity**: Results are specific to 40 harm intents from the ATLAS intent set and 8 model versions tested in May 2026. Generalisation to other intent distributions, harm categories, or subsequent model versions is not established.

---

## References

[1] Mazeika, M. et al. (2024). "HarmBench: A Standardized Evaluation Framework for Automated Red Teaming and Robust Refusal." *ICML 2024.* arxiv:2402.04249

[2] Chao, P. et al. (2023). "Jailbreaking Black Box Large Language Models in Twenty Queries." *NeurIPS 2023 SoLaR Workshop.* arxiv:2310.08419

[3] Mehrotra, A. et al. (2023). "Tree of Attacks with Pruning (TAP): Jailbreaking Black-Box LLMs Automatically." *NeurIPS 2024.* arxiv:2312.02119

[4] Chao, P. et al. (2024). "JailbreakBench: An Open Robustness Benchmark for Jailbreaking Large Language Models." *NeurIPS 2024.* arxiv:2404.01318

[5] Andriushchenko, M. et al. (2024). "Jailbreaking Leading Safety-Aligned LLMs with Simple Adaptive Attacks." *ICLR 2025.* arxiv:2404.02151

[6] Russinovich, M. et al. (2024). "The Crescendo Multi-Turn LLM Jailbreak Attack." *USENIX Security 2025.* arxiv:2404.01833

[7] Hagendorff, T. et al. (2026). "Large reasoning models are autonomous jailbreak agents." *Nature Communications* 17, 1435. PMC: PMC12881495

[8] Hughes, E. et al. (2024). "Best-of-N Jailbreaking." arxiv:2412.03556

[9] Liao, Z. et al. (2024). "AmpleGCG: Learning a Universal and Transferable Generative Model of Adversarial Suffixes for Jailbreaking Both Open and Closed LLMs." arxiv:2404.07921

[10] Li, H. et al. (2024). "Multi-Turn Jailbreak Attack on Large Language Models." arxiv:2410.01326

[11] Yang, Z. et al. (2024). "Chain of Attack: a Semantic-Driven Contextual Multi-Turn Attacker for LLM." arxiv:2405.05610

[12] Zeng, Y. et al. (2024). "How Johnny Can Persuade LLMs to Jailbreak Them: Rethinking Persuasion to Challenge AI Safety by Humanizing LLMs." *ACL 2024.* arxiv:2401.06373
