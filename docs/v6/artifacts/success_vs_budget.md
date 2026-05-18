# Success-vs-Budget Curves

Disentangling whether BoK reaches PAIR-5 because of **static diversity**, **repeated independent trials**, or **adaptive refinement with target feedback**.

## Overall ASR by Target-Call Budget

| Budget | PAIR-5 (adaptive) | BoK (diverse) | BoK-iid | PAIR-1 x K (iid) | Direct x K (iid) |
|--------|-------------------|---------------|---------|-------------------|-------------------|
| 1 | 68.1% [62.8, 73.0] | 56.2% [50.8, 61.6] | 65.8% | 64.1% | 15.9% |
| 2 | 84.7% [80.3, 88.2] | 77.5% [72.6, 81.7] | 88.3% | 87.1% | 29.3% |
| 3 | 90.3% [86.6, 93.1] | 84.1% [79.7, 87.7] | 96.0% | 95.4% | 40.6% |
| 4 | 92.5% [89.1, 94.9] | 88.1% [84.1, 91.2] | 98.6% | 98.3% | 50.1% |
| 5 | 93.8% [90.5, 95.9] | 91.2% [87.6, 93.9] | 99.5% | 99.4% | 58.0% |

## Scaling Decomposition (pooled, percentage points)

- **Diversity gain** = BoK(K) - BoK(1): raw improvement from having K diverse variants.
- **Correlation tax** = BoK-iid(K) - BoK(K): how much positive within-intent correlation reduces scaling vs. the i.i.d. theoretical ceiling. A large tax means vulnerability is an attribute of the (model, intent) pair, not independent per variant.
- **Adaptive premium** = PAIR(K) - BoK(K): benefit of target feedback over static diversity.

| Budget | Diversity gain | Correlation tax | Adaptive premium | BoK-iid ceiling |
|--------|---------------|-----------------|------------------|----------------|
| 1 | +0.0pp | +9.6pp | +11.9pp | 65.8% |
| 2 | +21.2pp | +10.8pp | +7.2pp | 88.3% |
| 3 | +27.8pp | +11.9pp | +6.2pp | 96.0% |
| 4 | +31.9pp | +10.5pp | +4.4pp | 98.6% |
| 5 | +35.0pp | +8.3pp | +2.5pp | 99.5% |

## Per-Model Comparison at K=1 and K=5

| Model | BoK@1 | PAIR@1 | BoK@5 | PAIR@5 | Div. gain @5 | Corr. tax @5 | Adapt. prem. @5 |
|-------|-------|--------|-------|--------|-------------|-------------|----------------|
| claude-sonnet-4 | 25.0% | 32.5% | 60.0% | 60.0% | +35.0pp | +27.9pp | +0.0pp |
| deepseek-chat-v3-0324 | 72.5% | 80.0% | 97.5% | 100.0% | +25.0pp | +2.5pp | +2.5pp |
| gemini-2.5-flash | 52.5% | 60.0% | 90.0% | 100.0% | +37.5pp | +9.1pp | +10.0pp |
| gpt-4o | 40.0% | 62.5% | 92.5% | 100.0% | +52.5pp | +5.9pp | +7.5pp |
| gpt-4o-mini | 35.0% | 55.0% | 95.0% | 95.0% | +60.0pp | +2.6pp | +0.0pp |
| llama-3.3-70b-instruct | 65.0% | 75.0% | 97.5% | 97.5% | +32.5pp | +2.4pp | +0.0pp |
| mistral-large-2411 | 90.0% | 95.0% | 97.5% | 100.0% | +7.5pp | +2.5pp | +2.5pp |
| qwen-2.5-72b-instruct | 70.0% | 85.0% | 100.0% | 97.5% | +30.0pp | +-0.1pp | -2.5pp |

## Full Per-Model Budget Curves

### claude-sonnet-4

| Budget | PAIR-5 | BoK | BoK-iid | Div. gain | Corr. tax | Adapt. prem. |
|--------|--------|-----|---------|-----------|-----------|-------------|
| 1 | 32.5% | 25.0% | 34.5% | +0.0pp | +9.5pp | +7.5pp |
| 2 | 42.5% | 42.5% | 57.1% | +17.5pp | +14.6pp | +0.0pp |
| 3 | 52.5% | 52.5% | 71.9% | +27.5pp | +19.4pp | +0.0pp |
| 4 | 57.5% | 57.5% | 81.6% | +32.5pp | +24.1pp | +0.0pp |
| 5 | 60.0% | 60.0% | 87.9% | +35.0pp | +27.9pp | +0.0pp |

### deepseek-chat-v3-0324

| Budget | PAIR-5 | BoK | BoK-iid | Div. gain | Corr. tax | Adapt. prem. |
|--------|--------|-----|---------|-----------|-----------|-------------|
| 1 | 80.0% | 72.5% | 80.5% | +0.0pp | +8.0pp | +7.5pp |
| 2 | 92.5% | 90.0% | 96.2% | +17.5pp | +6.2pp | +2.5pp |
| 3 | 100.0% | 92.5% | 99.3% | +20.0pp | +6.8pp | +7.5pp |
| 4 | 100.0% | 97.5% | 99.9% | +25.0pp | +2.4pp | +2.5pp |
| 5 | 100.0% | 97.5% | 100.0% | +25.0pp | +2.5pp | +2.5pp |

### gemini-2.5-flash

| Budget | PAIR-5 | BoK | BoK-iid | Div. gain | Corr. tax | Adapt. prem. |
|--------|--------|-----|---------|-----------|-----------|-------------|
| 1 | 60.0% | 52.5% | 61.0% | +0.0pp | +8.5pp | +7.5pp |
| 2 | 90.0% | 77.5% | 84.8% | +25.0pp | +7.3pp | +12.5pp |
| 3 | 92.5% | 82.5% | 94.1% | +30.0pp | +11.6pp | +10.0pp |
| 4 | 97.5% | 87.5% | 97.7% | +35.0pp | +10.2pp | +10.0pp |
| 5 | 100.0% | 90.0% | 99.1% | +37.5pp | +9.1pp | +10.0pp |

### gpt-4o

| Budget | PAIR-5 | BoK | BoK-iid | Div. gain | Corr. tax | Adapt. prem. |
|--------|--------|-----|---------|-----------|-----------|-------------|
| 1 | 62.5% | 40.0% | 56.5% | +0.0pp | +16.5pp | +22.5pp |
| 2 | 87.5% | 72.5% | 81.1% | +32.5pp | +8.6pp | +15.0pp |
| 3 | 95.0% | 85.0% | 91.8% | +45.0pp | +6.8pp | +10.0pp |
| 4 | 97.5% | 87.5% | 96.4% | +47.5pp | +8.9pp | +10.0pp |
| 5 | 100.0% | 92.5% | 98.4% | +52.5pp | +5.9pp | +7.5pp |

### gpt-4o-mini

| Budget | PAIR-5 | BoK | BoK-iid | Div. gain | Corr. tax | Adapt. prem. |
|--------|--------|-----|---------|-----------|-----------|-------------|
| 1 | 55.0% | 35.0% | 52.5% | +0.0pp | +17.5pp | +20.0pp |
| 2 | 77.5% | 67.5% | 77.4% | +32.5pp | +9.9pp | +10.0pp |
| 3 | 90.0% | 80.0% | 89.3% | +45.0pp | +9.3pp | +10.0pp |
| 4 | 95.0% | 87.5% | 94.9% | +52.5pp | +7.4pp | +7.5pp |
| 5 | 95.0% | 95.0% | 97.6% | +60.0pp | +2.6pp | +0.0pp |

### llama-3.3-70b-instruct

| Budget | PAIR-5 | BoK | BoK-iid | Div. gain | Corr. tax | Adapt. prem. |
|--------|--------|-----|---------|-----------|-----------|-------------|
| 1 | 75.0% | 65.0% | 75.0% | +0.0pp | +10.0pp | +10.0pp |
| 2 | 92.5% | 87.5% | 93.8% | +22.5pp | +6.2pp | +5.0pp |
| 3 | 97.5% | 95.0% | 98.4% | +30.0pp | +3.4pp | +2.5pp |
| 4 | 97.5% | 97.5% | 99.6% | +32.5pp | +2.1pp | +0.0pp |
| 5 | 97.5% | 97.5% | 99.9% | +32.5pp | +2.4pp | +0.0pp |

### mistral-large-2411

| Budget | PAIR-5 | BoK | BoK-iid | Div. gain | Corr. tax | Adapt. prem. |
|--------|--------|-----|---------|-----------|-----------|-------------|
| 1 | 95.0% | 90.0% | 91.0% | +0.0pp | +1.0pp | +5.0pp |
| 2 | 100.0% | 95.0% | 99.2% | +5.0pp | +4.2pp | +5.0pp |
| 3 | 100.0% | 95.0% | 99.9% | +5.0pp | +4.9pp | +5.0pp |
| 4 | 100.0% | 95.0% | 100.0% | +5.0pp | +5.0pp | +5.0pp |
| 5 | 100.0% | 97.5% | 100.0% | +7.5pp | +2.5pp | +2.5pp |

### qwen-2.5-72b-instruct

| Budget | PAIR-5 | BoK | BoK-iid | Div. gain | Corr. tax | Adapt. prem. |
|--------|--------|-----|---------|-----------|-----------|-------------|
| 1 | 85.0% | 70.0% | 75.5% | +0.0pp | +5.5pp | +15.0pp |
| 2 | 95.0% | 87.5% | 94.0% | +17.5pp | +6.5pp | +7.5pp |
| 3 | 95.0% | 90.0% | 98.5% | +20.0pp | +8.5pp | +5.0pp |
| 4 | 95.0% | 95.0% | 99.6% | +25.0pp | +4.6pp | +0.0pp |
| 5 | 97.5% | 100.0% | 99.9% | +30.0pp | +-0.1pp | -2.5pp |

## ASCII Budget Curves (for quick visual reference)

```
Budget   PAIR-5   BoK     BoK-iid  PAIR-1xK  DirectxK
  K=1     68.1  ###########################
          56.2  ######################
          65.8  ##########################
          64.1  #########################
          15.9  ######
         ----
  K=2     84.7  #################################
          77.5  ###############################
          88.3  ###################################
          87.1  ##################################
          29.3  ###########
         ----
  K=3     90.3  ####################################
          84.1  #################################
          96.0  ######################################
          95.4  ######################################
          40.6  ################
         ----
  K=4     92.5  #####################################
          88.1  ###################################
          98.6  #######################################
          98.3  #######################################
          50.1  ####################
         ----
  K=5     93.8  #####################################
          91.2  ####################################
          99.5  #######################################
          99.4  #######################################
          58.0  #######################
```

## Key Findings

1. **BoK and PAIR-5 converge at K=5**: BoK 91.2% vs PAIR-5 93.8% (delta = 2.5pp). Both far exceed single-shot baselines.

2. **K-scaling is powerful but correlation-limited**: the i.i.d. ceiling at K=5 is 99.5% (mean per-variant rate p=65.8%), but actual BoK only reaches 91.2%. The **correlation tax is +8.3pp** — vulnerability is largely a property of the (model, intent) pair, so diverse strategies tend to succeed or fail together.

3. **Diversity still adds +35.0pp over single-shot**: BoK scales from 56.2% (K=1) to 91.2% (K=5), a large gain even if it falls short of the i.i.d. optimum. The bulk of the gain arrives by K=3 (84.1%).

4. **Adaptive refinement matters most at low budget**: at K=1, PAIR leads BoK by 11.9pp (68.1% vs 56.2%), reflecting the value of LLM-guided prompt crafting. By K=5, the adaptive premium shrinks to +2.5pp as BoK's diversity catches up.

5. **PAIR front-loads success**: 218 of 320 attacks (68.1%) succeed on PAIR's first iteration. Refinement adds only +25.6pp across iterations 2-5, confirming that the attacker LLM's first-shot reasoning is the dominant factor.

6. **Implication for Best-of-N jailbreaking**: even with strong positive correlation, K-scaling lifts ASR by ~35pp (56% to 91%). The correlation tax means that extrapolating i.i.d. scaling laws (Hughes et al.) to diverse-strategy BoK overpredicts success; real gains saturate faster. Adaptive methods like PAIR are more query-efficient at low budgets, but static BoK closes the gap at K>=3.
