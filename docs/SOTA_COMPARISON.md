# SOTA Baseline Comparison for ATLAS Experiment

Collected from peer-reviewed research. All numbers verified against source tables.

---

## 1. PAIR — Single-Turn Adaptive (Black-Box)

**Source:** Tables 2-4 in Andriushchenko et al. (ICLR 2025, arxiv:2404.02151), citing Chao et al. 2023 and Mazeika et al. 2024 (HarmBench)

| Target Model | PAIR ASR | Source |
| --- | --- | --- |
| GPT-3.5 Turbo | 60% | Chao et al. 2023 |
| GPT-4 Turbo | 33% | Mazeika et al. 2024* |
| Claude 2.0 | 4% | Chao et al. 2023 |
| Llama-2-Chat-7B | 10% | Chao et al. 2023 |
| Llama-2-Chat-13B | 15% | Mazeika et al. 2024* |
| Llama-2-Chat-70B | 15% | Mazeika et al. 2024* |
| R2D2-7B | 48% | Mazeika et al. 2024* |

*Note: entries marked * use "different sets of harmful requests" and judges than the main paper — not directly comparable.*

**No PAIR results exist in the literature for:** GPT-4o, Claude 3.x, Claude 3.5 Sonnet, Llama-3, Gemini.

### Our ATLAS adaptive_single_turn (PAIR with DeepSeek-R1 attacker, 5 iters)

From experiment `20260505_003630`, raw 3-judge majority vote (pre-review):

| Target Model | Our ASR | N |
| --- | --- | --- |
| GPT-4o-mini | 87.5% | 40 |
| GPT-4o | 90.0% | 40 |
| Claude Sonnet 4 | 42.5% | 40 |
| Gemini 2.5 Flash | 92.5% | 40 |
| Llama 3.3 70B | 90.0% | 40 |
| DeepSeek V3 | 92.5% | 40 |
| Qwen 2.5 72B | 90.0% | 40 |
| Mistral Large | 95.0% | 40 |

Our higher ASR vs literature PAIR is expected: we use a reasoning model (DeepSeek-R1) as attacker.

---

## 2. TAP — Single-Turn Tree Search (Black-Box)

**Source:** Tables 2-3 in Andriushchenko et al. (ICLR 2025), citing Zeng et al. 2024 and Mazeika et al. 2024

| Target Model | TAP ASR | Source |
| --- | --- | --- |
| GPT-3.5 Turbo | 80% | Zeng et al. 2024 |
| GPT-4 Turbo | 36% | Mazeika et al. 2024* |
| GPT-4 Turbo (transfer) | 59% | Mazeika et al. 2024* |
| Llama-2-Chat-7B | 4% | Zeng et al. 2024 |
| Llama-2-Chat-13B | 14% | Mazeika et al. 2024* |
| Llama-2-Chat-70B | 13% | Mazeika et al. 2024* |
| R2D2-7B | 61% | Mazeika et al. 2024* |

---

## 3. Adaptive Attacks — Model-Specific (ICLR 2025)

**Source:** Andriushchenko et al. "Jailbreaking Leading Safety-Aligned LLMs with Simple Adaptive Attacks" (ICLR 2025, arxiv:2404.02151)

Uses model-specific prompt templates + random search + self-transfer. Tables 2-4:

| Target Model | Best Prior ASR | Their Method ASR |
| --- | --- | --- |
| GPT-3.5 Turbo | 94% (PAP) | 100% (Prompt) |
| GPT-4 Turbo | 59% (TAP transfer) | 96% (Prompt+RS+Transfer) |
| GPT-4o | N/A | 100% (Custom+RS+Transfer) |
| Claude 2.0 | 61% (Persona Mod.) | 100% (Prefilling) |
| Claude 3 Haiku | N/A | 100% (Prefilling) |
| Claude 3 Sonnet | N/A | 100% (Prefilling+Transfer) |
| Claude 3.5 Sonnet | N/A | 100% (Prefilling) |
| Claude 3 Opus | N/A | 100% (Prefilling) |
| Llama-2-Chat-7B | 92% (PAP) | 100% (Prompt+RS+Transfer) |
| Llama-2-Chat-70B | 38% (GCG) | 100% (Prompt+RS+Transfer) |
| Llama-3-Instruct-8B | N/A | 100% (Prompt+RS) |

*Note: Prefilling attack requires API-level access to force assistant prefix — not a pure black-box attack.*

---

## 4. Autonomous Reasoning Model Attacks (Nature Communications 2026)

**Source:** Hagendorff et al. "Large reasoning models are autonomous jailbreak agents" Nature Communications 17, 1435 (2026). PMC: PMC12881495.

Attackers: DeepSeek-R1, Gemini 2.5 Flash, Grok 3 Mini, Qwen3 235B
Benchmark: 70 harmful requests, 7 categories, 10-turn multi-turn conversations
Overall ASR: 97.14%
Human-LLM judge agreement: ICC = 0.925

| Target Model | Max Harm Score (%) |
| --- | --- |
| DeepSeek-V3 | 90.0% |
| Gemini 2.5 Flash | 71.43% |
| Qwen3 30B | 71.43% |
| GPT-4o | 61.43% |
| o4-mini | 34.29% |
| Llama 3.1 70B | 32.86% |
| Claude 4 Sonnet | 2.86% |

Control baseline (direct prompt): average harm < 0.5

---

## 5. Crescendo — Multi-Turn Gradual Escalation (USENIX Security 2025)

**Source:** Russinovich et al. "The Crescendo Multi-Turn LLM Jailbreak Attack" (USENIX Security 2025, arxiv:2404.01833)

Qualitative results — paper reports ranges by task category, not single ASR numbers:

| Target Model | ASR Range | Direct Baseline | Avg Turns |
| --- | --- | --- | --- |
| GPT-4 | 20-100% (task-dependent) | ~0% most tasks | <5 |
| GPT-3.5 | 20-100% | ~0% | <5 |
| Gemini Pro | 60-100% | ~0% | <5 |
| Llama-2 70B | 20-80% | ~0% | <5 |

*Note: ASR varies significantly by task category. "Explicit content" tasks have near-0% ASR, while misinformation tasks reach 100%.*

### Our ATLAS adaptive_multi_turn (DeepSeek-R1 attacker, 5 turns max)

| Target Model | Our ASR | N |
| --- | --- | --- |
| GPT-4o-mini | 80.0% | 40 |
| GPT-4o | 67.5% | 40 |
| Claude Sonnet 4 | 20.0% | 40 |
| Gemini 2.5 Flash | 70.0% | 40 |
| Llama 3.3 70B | 62.5% | 40 |
| DeepSeek V3 | 62.5% | 40 |
| Qwen 2.5 72B | 72.5% | 40 |
| Mistral Large | 72.5% | 40 |

---

## 6. Static Attacks — Our Baselines

### Jailbreak (static single-turn, template-based)

| Target Model | Our ASR | N |
| --- | --- | --- |
| GPT-4o-mini | 20.3% | 64 |
| GPT-4o | 17.2% | 64 |
| Claude Sonnet 4 | 0.0% | 64 |
| Gemini 2.5 Flash | 92.2% | 64 |
| Llama 3.3 70B | 81.2% | 64 |
| DeepSeek V3 | 50.0% | 64 |
| Qwen 2.5 72B | 18.8% | 64 |
| Mistral Large | 90.6% | 64 |

### Scripted Multi-Turn (static escalation, no attacker LLM)

| Target Model | Our ASR | N |
| --- | --- | --- |
| GPT-4o-mini | 37.5% | 40 |
| GPT-4o | 37.5% | 40 |
| Claude Sonnet 4 | 32.5% | 40 |
| Gemini 2.5 Flash | 55.0% | 40 |
| Llama 3.3 70B | 55.0% | 40 |
| DeepSeek V3 | 57.5% | 40 |
| Qwen 2.5 72B | 67.5% | 40 |
| Mistral Large | 67.5% | 40 |

---

## 7. Comparison Summary

### Model Robustness Ranking

| Rank | Nature 2026 (autonomous attackers) | Our Experiment (PAIR, R1 attacker) |
| --- | --- | --- |
| 1 (safest) | Claude 4 Sonnet (2.86%) | Claude Sonnet 4 (42.5% / 20.0%) |
| 2 | Llama 3.1 70B (32.86%) | GPT-4o-mini (87.5% / 80.0%) |
| 3 | o4-mini (34.29%) | GPT-4o (90.0% / 67.5%) |
| 4 | GPT-4o (61.43%) | Llama 3.3 70B (90.0% / 62.5%) |
| 5+ | Gemini/Qwen/DeepSeek (70%+) | Gemini/DeepSeek/Qwen/Mistral (90%+) |

Claude's dominance as the most resistant model is consistent across studies.

### Key Differences From Literature

1. **Our PAIR ASR is higher** (87-95%) than original PAIR (4-60%) because we use DeepSeek-R1 (reasoning model) as attacker vs GPT-4 in the original paper
2. **Single-turn > multi-turn** in our experiment — consistent with M2S (ACL 2025) finding
3. **Gemini is surprisingly vulnerable** to static jailbreaks (92.2%) but the Nature 2026 study also shows 71.4% vulnerability

---

## References

1. Chao et al. (2023). "Jailbreaking Black-Box LLMs in Twenty Queries." arxiv:2310.08419
2. Mehrotra et al. (2023). "Tree of Attacks with Pruning." arxiv:2312.02119
3. Mazeika et al. (2024). "HarmBench." arxiv:2402.04249 (ICLR 2025)
4. Chao et al. (2024). "JailbreakBench." arxiv:2404.01318 (NeurIPS 2024)
5. Andriushchenko et al. (2024). "Jailbreaking Leading Safety-Aligned LLMs with Simple Adaptive Attacks." arxiv:2404.02151 (ICLR 2025)
6. Russinovich et al. (2024). "The Crescendo Multi-Turn LLM Jailbreak Attack." arxiv:2404.01833 (USENIX Security 2025)
7. Hagendorff et al. (2026). "Large reasoning models are autonomous jailbreak agents." Nature Comms 17, 1435
