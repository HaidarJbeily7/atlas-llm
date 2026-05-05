# SOTA Baselines for ATLAS Experiment

Based on supervisor feedback: "we might also need to add at least one strong SOTA baseline. The minimum realistic baseline is HarmBench-style static/direct attack plus PAIR or TAP-style adaptive single-turn."

---

## 1. HarmBench-Style Static/Direct Attack

**What it is:** Take attack intents and feed them directly to the target model with no obfuscation, jailbreak template, or attacker LLM. This is the zero-effort baseline that establishes the floor — how often does the model comply with no attack strategy at all?

**Reference:** Mazeika et al., 2024 — *HarmBench: A Standardized Evaluation Framework for Automated Red Teaming and Robust Refusal*

**Key details:**
- Uses standardized prompt format and classifier for judging success
- Maps to the **Static Single-Turn** cell in our 2x2 design
- Must follow HarmBench's exact protocol (prompt format + evaluation methodology) for credibility

**Implementation in ATLAS:**
- Implement a `DirectAttackProbe` (or adapt the existing static single-turn probe to follow HarmBench's protocol exactly)
- Use the same intents and target models as the 2x2 conditions

---

## 2. PAIR — Prompt Automatic Iterative Refinement

**What it is:** An attacker LLM iteratively refines a single jailbreak prompt over multiple self-improvement rounds, but the target only ever sees **one final prompt**. Adaptive single-turn.

**Reference:** Chao et al., 2023 — *Jailbreaking Black-Box Large Language Models in Twenty Queries*

**Key details:**
- Attacker LLM generates a candidate jailbreak prompt
- Target model responds; attacker evaluates and refines
- Iterates for a fixed budget (typically ~20 iterations)
- Target sees exactly one prompt per attempt — the best one found
- Open-source implementation available in HarmBench's repo

---

## 3. TAP — Tree of Attacks with Pruning

**What it is:** Similar to PAIR but uses a **tree-search** strategy. The attacker explores multiple candidate prompts in a branching structure, pruning unpromising branches. Also adaptive single-turn.

**Reference:** Mehrotra et al., 2023 — *Tree of Attacks: Jailbreaking Black-Box LLMs with Automatically Generated Prompts*

**Key details:**
- Branching exploration of prompt candidates (wider search than PAIR)
- Pruning mechanism discards low-quality attack branches early
- Generally achieves higher ASR than PAIR at similar or lower cost
- Also available in HarmBench's repo

---

## Why These Baselines Matter

Without them, a reviewer will ask: "How does this compare to established attack methods in the literature?"

Adding PAIR/TAP baselines allows us to:
1. **Calibrate** results against known SOTA methods
2. **Make ASR numbers interpretable** (e.g., "our adaptive multi-turn achieves X% higher ASR than PAIR")
3. **Strengthen credibility** — shows we're not evaluating in a vacuum

---

## What to Implement (Minimum)

1. **DirectAttackProbe** — HarmBench-style static baseline
2. **At least one of PAIR or TAP** as an `AdaptiveSingleTurnProbe` variant
3. Run both on the **same intents and target models** as the 2x2 conditions
4. Report ASR, cost, and token usage for direct comparison

The professor's phrasing ("minimum realistic") signals this is the bare minimum to pass peer review. Ideally, implement both PAIR and TAP.

---

## Resources

- HarmBench repo (includes PAIR and TAP implementations): https://github.com/centerforaisafety/HarmBench
- PAIR paper: https://arxiv.org/abs/2310.08419
- TAP paper: https://arxiv.org/abs/2312.02119
- HarmBench paper: https://arxiv.org/abs/2402.04249
