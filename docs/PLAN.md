# ATLAS Experiment Redesign Plan

Based on supervisor feedback (April 2025). The core concern is that the current setup **conflates adaptivity with multi-turn interaction**, making it impossible to attribute gains to one factor over the other.

---

## 1. Redesign as a 2x2 Factorial Study

Replace the current experimental conditions with a 2x2 design that crosses **adaptivity** (static vs. adaptive) with **interaction mode** (single-turn vs. multi-turn):

| | Single-Turn | Multi-Turn |
|---|---|---|
| **Static** | Fixed prompts, one shot | Scripted multi-turn sequences (no attacker LLM) |
| **Adaptive** | Attacker LLM refines prompt in one shot (generate-then-attack) | Attacker LLM refines across turns (current crescendo) |

### What needs to happen in ATLAS

- [ ] **Static Single-Turn condition**: Already exists — standard `BaseProbe` with fixed prompts.
- [ ] **Adaptive Single-Turn condition**: New probe type. Use the attacker LLM to generate/refine a single optimised prompt (no conversation history with the target). The attacker may iterate internally, but the target sees exactly one message.
- [ ] **Scripted Multi-Turn condition**: New probe type. Pre-defined multi-turn scripts (e.g., 3–5 turns) with no attacker LLM involvement. Scripts should cover the same intents as the other conditions.
- [ ] **Adaptive Multi-Turn condition**: Already exists — `CrescendoProbe` / `AdaptiveProbe` with multi-turn conversation.
- [ ] Ensure all four conditions share the **same set of attack intents** so results are directly comparable.

---

## 2. RQ1 — Attack Budget & Cost Accounting

> "Define budget carefully and count total attack cost, not only target-model tokens."

### Metrics to track per attempt

- [ ] **Target-model tokens**: input + output tokens consumed on the target LLM.
- [ ] **Attacker-model tokens**: input + output tokens consumed by the attacker/judge LLM (zero for static conditions).
- [ ] **Total tokens**: sum of target + attacker tokens.
- [ ] **Dollar cost**: compute from per-token pricing of each model/provider.
- [ ] **Wall-clock latency**: end-to-end time per attempt (including retries).
- [ ] **Number of turns / API calls**: to the target and to the attacker separately.

### Implementation in ATLAS

- [ ] Extend `Attempt` / `Finding` models to carry `attacker_tokens_in`, `attacker_tokens_out`, `cost_usd`, `latency_ms`.
- [ ] Update `LiteLLMGenerator` to surface token counts from the LiteLLM response.
- [ ] Add a `CostCalculator` utility that maps (model, token_count) → USD using a pricing table.
- [ ] Aggregate budget metrics in `ScanResult` (total cost, mean cost per successful attack, etc.).

### Statistical Analysis (RQ1)

- [ ] **Paired design**: every attack intent is tested under all four conditions × all target models. Pair results by (intent, model).
- [ ] **Effect sizes**: report Cohen's d or odds ratios for ASR differences between conditions.
- [ ] **Confidence intervals**: 95% CIs for ASR differences (bootstrap or exact binomial).
- [ ] **McNemar as supplement, not primary**: keep McNemar for the paired binary comparison but lead with effect sizes + CIs.
- [ ] Report cost-effectiveness: ASR per dollar, ASR per 1K tokens.

---

## 3. RQ2 — Failure-Type Distribution & Human Validation

> "Stronger comparison of failure-type distributions, plus a human-validated subset."

### Failure-type analysis

- [ ] Define a taxonomy of failure types (e.g., full compliance, partial leak, hedged compliance, refusal-then-comply, role-play compliance, etc.).
- [ ] Classify every successful attack by failure type (can be automated first pass via `LLMJudgeDetector` with a classification prompt).
- [ ] Compare failure-type distributions across the four conditions using chi-squared or Fisher's exact test.
- [ ] Visualise distributions per condition as stacked bar charts or mosaic plots.

### Human annotation protocol

- [ ] Sample a **stratified subset** (e.g., 200 attempts: 50 per condition, balanced across intents and models).
- [ ] Recruit **at least 2 independent annotators**.
- [ ] Provide annotation guidelines with:
  - Failure-type definitions and examples.
  - Binary safe/unsafe judgement.
  - Severity rating (matches detector output or not).
- [ ] Compute **inter-annotator agreement** (Cohen's kappa).
- [ ] **Adjudication round**: a third annotator or discussion resolves disagreements.
- [ ] Report agreement statistics and compare human labels against automated detector labels to quantify detector accuracy.

---

## 4. Detector Sensitivity as a Contribution

> "Detector sensitivity is important enough that it may become part of the contribution rather than just a control."

### Promote to RQ3 (or elevate within existing RQs)

- [ ] **RQ3 (proposed)**: How sensitive are automated safety detectors to attack sophistication and interaction mode?
- [ ] Evaluate each detector type (`KeywordDetector`, `RefusalDetector`, `LLMJudgeDetector`, `SemanticJudgeDetector`, etc.) independently on the same data.
- [ ] Report per-detector: precision, recall, F1, and ROC-AUC against human ground-truth labels.
- [ ] Analyse whether detector performance degrades across conditions (e.g., do keyword detectors miss adaptive attacks more than static ones?).
- [ ] Compare ATLAS detectors against recent LLM-as-judge baselines from the literature (cite: recent judge papers — e.g., JudgeBench, LLM-as-Judge surveys).
- [ ] Discuss implications: if detectors are condition-sensitive, reported ASR is detector-dependent, which changes interpretation of RQ1/RQ2.

### Implementation in ATLAS

- [ ] Run **all detectors in parallel** on every attempt (not just the probe's default detector) to collect a full detection matrix.
- [ ] Store per-detector results in the `Finding` model (add a `detector_results: dict[str, DetectorResult]` field).
- [ ] Add analysis scripts to compute detector agreement and performance metrics.

---

## 5. Summary of New/Modified ATLAS Components

| Component | Status | Action |
|---|---|---|
| `AdaptiveSingleTurnProbe` | New | Attacker LLM generates one optimised prompt |
| `ScriptedMultiTurnProbe` | New | Pre-written multi-turn scripts, no attacker LLM |
| `Attempt` / `Finding` models | Modify | Add cost, latency, attacker-token, multi-detector fields |
| `LiteLLMGenerator` | Modify | Surface token counts |
| `CostCalculator` | New | Model pricing → USD conversion |
| `ScanResult` | Modify | Aggregate budget metrics |
| Detection matrix | New | Run all detectors on every attempt |
| Analysis scripts | New | Effect sizes, CIs, chi-squared, kappa, ROC |
| Human annotation toolkit | New | Sampling, guidelines, adjudication workflow |

---

## 6. Execution Order

1. **Define shared intent set** — curate the attack intents that all four conditions will use.
2. **Implement `AdaptiveSingleTurnProbe` and `ScriptedMultiTurnProbe`** — the two missing cells.
3. **Add cost/token tracking** to generator and data models.
4. **Run all detectors in parallel** and store full detection matrix.
5. **Run the 2x2 experiment** across target models.
6. **Automated analysis** — ASR, effect sizes, CIs, failure-type distributions, detector metrics.
7. **Human annotation** — sample, annotate, adjudicate, compute agreement.
8. **Write up** — RQ1 (budget-aware ASR comparison), RQ2 (failure types + human validation), RQ3 (detector sensitivity).
