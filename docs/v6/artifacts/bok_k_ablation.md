# BoK K=1/3/5 Ablation Analysis

## Overall Results

| K | Total | Successes | ASR | 95% CI | Marginal Gain |
|---|-------|-----------|-----|--------|--------------|
| 1 | 320 | 180 | 56.2% | [50.8%, 61.6%] | — |
| 3 | 320 | 269 | 84.1% | [79.7%, 87.7%] | — |
| 5 | 320 | 292 | 91.2% | [87.6%, 93.9%] | +7.2pp |

## Per-Model Results

| Model | K=1 ASR | K=3 ASR | K=5 ASR | Marginal Gain (3→5) |
|-------|---------|---------|---------|--------------------|
| claude-sonnet-4 | 25.0% | 52.5% | 60.0% | +7.5pp |
| deepseek-chat-v3-0324 | 72.5% | 92.5% | 97.5% | +5.0pp |
| gemini-2.5-flash | 52.5% | 82.5% | 90.0% | +7.5pp |
| gpt-4o | 40.0% | 85.0% | 92.5% | +7.5pp |
| gpt-4o-mini | 35.0% | 80.0% | 95.0% | +15.0pp |
| llama-3.3-70b-instruct | 65.0% | 95.0% | 97.5% | +2.5pp |
| mistral-large-2411 | 90.0% | 95.0% | 97.5% | +2.5pp |
| qwen-2.5-72b-instruct | 70.0% | 90.0% | 100.0% | +10.0pp |

## Analysis

- **K=1 to K=5 total gain**: +35.0 percentage points
- **K=3 to K=5 marginal gain**: +7.2pp (diminishing returns)
- **Optimal K**: K=5 achieves the highest ASR (91.2%) but with diminishing returns after K=3
