# Human-Validation Counterfactual: Conclusions That Would Be Wrong

This analysis compares the success-vs-budget curves computed from **raw detector verdicts** against **human-validated verdicts** (annotation ledger, 100% review coverage, Cohen's kappa = 0.81). It identifies specific scientific claims that would be incorrect without human validation.

## Budget Curves: Raw Detector vs Human-Validated

| K | BoK (raw) | BoK (human) | delta | PAIR-5 (raw) | PAIR-5 (human) | delta |
|---|-----------|-------------|-------|--------------|----------------|-------|
| 1 | 56.2% | 54.1% | +2.2pp | 62.8% | 64.1% | -1.2pp |
| 2 | 77.5% | 73.8% | +3.8pp | 77.2% | 78.1% | -0.9pp |
| 3 | 84.1% | 79.4% | +4.7pp | 81.9% | 83.1% | -1.2pp |
| 4 | 88.1% | 82.2% | +5.9pp | 83.8% | 84.7% | -0.9pp |
| 5 | 91.2% | 85.6% | +5.6pp | 85.0% | 85.9% | -0.9pp |

## Any-of-K False-Positive Accumulation (BoK)

Each additional variant gives the detector another chance to produce a false positive. A single FP variant at position i makes the finding a false positive for all K >= i.

| K | FP count | FN count | Raw ASR | Corrected ASR | Inflation |
|---|----------|----------|---------|---------------|-----------|
| 1 | 7 | 0 | 56.2% | 54.1% | +2.2pp |
| 2 | 12 | 0 | 77.5% | 73.8% | +3.8pp |
| 3 | 15 | 0 | 84.1% | 79.4% | +4.7pp |
| 4 | 19 | 0 | 88.1% | 82.2% | +5.9pp |
| 5 | 23 | 5 | 91.2% | 85.6% | +5.6pp |

## Per-Model Comparison at K=5: Raw vs Human-Validated

| Model | BoK raw | BoK human | PAIR raw | PAIR human | Raw winner | True winner |
|-------|---------|-----------|----------|------------|------------|------------|
| claude-sonnet-4 | 60.0% | 47.5% | 42.5% | 45.0% | BoK | BoK |
| deepseek-chat-v3-0324 | 97.5% | 95.0% | 92.5% | 100.0% | BoK | PAIR **INV** |
| gemini-2.5-flash | 90.0% | 87.5% | 92.5% | 92.5% | PAIR | PAIR |
| gpt-4o | 92.5% | 85.0% | 90.0% | 87.5% | BoK | PAIR **INV** |
| gpt-4o-mini | 95.0% | 87.5% | 87.5% | 87.5% | BoK | tie **INV** |
| llama-3.3-70b-instruct | 97.5% | 92.5% | 90.0% | 90.0% | BoK | BoK |
| mistral-large-2411 | 97.5% | 97.5% | 95.0% | 92.5% | BoK | BoK |
| qwen-2.5-72b-instruct | 100.0% | 92.5% | 90.0% | 92.5% | BoK | tie **INV** |

## Scientific Conclusions That Would Be Wrong

### 1. [!!!] Rank Inversion

**Without human validation**: BoK (91.2%) outperforms PAIR-5 (85.0%) by +6.2pp

**With human validation**: BoK (85.6%) and PAIR-5 (85.9%) are statistically tied (delta = -0.3pp)

**Mechanism**: BoK accumulates 23 FP across 5 variants (any-of-K amplification); PAIR-5 has net 3 FN (detector underreports adaptive attacks)

### 2. [!!] Inflated Diversity Gain

**Without human validation**: BoK diversity gain (K=1 to K=5) is +35.0pp

**With human validation**: BoK diversity gain is +31.6pp (3.4pp was FP inflation)

**Mechanism**: FP inflation grows with K: +2.2pp at K=1, +5.6pp at K=5. The any-of-K rule gives each additional variant another chance to produce a false positive.

### 3. [!!!] Phantom Adaptive Premium

**Without human validation**: Adaptive premium at K=5 is -6.2pp (PAIR trails BoK)

**With human validation**: Adaptive premium at K=5 is +0.3pp (methods are equivalent)

**Mechanism**: BoK's FP inflation inflates its ASR; PAIR's FN deflates its ASR. Together they create a spurious BoK advantage.

### 4. [!!] Per Model Inversions

**Without human validation**: 2 model(s) show BoK/PAIR rank inversion after human validation

**With human validation**: Per-model rankings change when FP/FN are corrected

  - **deepseek-chat-v3-0324**: raw BoK 97.5% vs PAIR 92.5% (BoK +5.0pp) → corrected BoK 95.0% vs PAIR 100.0% (BoK -5.0pp)
  - **gpt-4o**: raw BoK 92.5% vs PAIR 90.0% (BoK +2.5pp) → corrected BoK 85.0% vs PAIR 87.5% (BoK -2.5pp)

### 5. [!!!] Scripted Mt Overestimate

**Without human validation**: Scripted multi-turn (51.2% raw ASR) is a moderately effective baseline

**With human validation**: Scripted multi-turn (37.5% adjusted ASR) is weak; 13.7pp was FP inflation — the largest measurement error of any condition

**Mechanism**: Scripted dialogues produce ambiguous outputs that trigger detector FP. 51 of 320 findings were false positives (15.9% FP rate).

### 6. [!!!] Cost Efficiency Misjudgment

**Without human validation**: BoK (91.2%) is more effective than PAIR-5 (85.0%) despite using all 5 target calls

**With human validation**: PAIR-5 (85.9%) matches BoK (85.6%) while realizing only 1.6 target calls on average (68% fewer queries)

**Mechanism**: FP inflation in BoK masks PAIR's query efficiency advantage. Practitioners choosing BoK over PAIR based on raw ASR would use 3x more target queries for equivalent adjusted ASR.

## Summary: Why Human Validation Is Non-Negotiable

| Aspect | Raw detector | Human-validated | Error type |
|--------|-------------|-----------------|------------|
| Best method at K=5 | BoK (91.2%) | Tie (85.6% vs 85.9%) | Rank inversion |
| BoK diversity gain (K=1→5) | +35.0pp | +31.6pp | Inflated by FP accumulation |
| Adaptive premium (K=5) | -6.2pp | +0.3pp | Sign/magnitude error |
| Scripted MT baseline | 51.2% (moderate) | 37.5% (weak) | 13.7pp overestimate |
| Cost-efficiency winner | BoK (higher ASR) | PAIR (same ASR, 68% fewer queries) | Wrong recommendation |

Without human validation, a practitioner would (1) choose BoK over PAIR despite PAIR being 3x more query-efficient at equivalent true ASR, (2) overestimate the value of static diversity by ~7%, and (3) misjudge scripted attacks as a viable baseline. Every cross-condition comparison in this study required human validation to be directionally correct.
