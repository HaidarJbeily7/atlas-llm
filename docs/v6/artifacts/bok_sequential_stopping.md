# BoK Sequential Stopping Simulation

## Overall Results

### Query Efficiency

- **Mean realized queries**: 1.94/5.0 (38.8% of max cap)
- **Median realized queries**: 1.0/5
- **Theoretical query savings**: 61.2% (proportional cost savings)

### Stopping Distribution

| Stop Point | Percentage |
|------------|-----------|
| Variant 1 | 56.2% |
| Variant 2 | 21.2% |
| Variant 3 | 6.6% |
| Variant 4 | 4.1% |
| Variant 5 | 3.1% |
| Never (all failed) | 8.8% |

## Per-Model Results

| Model | Mean Realized | Theoretical Savings | Stop at V1 | Stop at V2 | Stop at V3 | Never |
|-------|---------------|---------------------|-------------|-------------|-------------|-------|
| claude-sonnet-4 | 3.2/5.0 | 35.5% | 0.0% | 0.0% | 0.0% | 40.0% |
| deepseek-chat-v3-0324 | 1.5/5.0 | 70.5% | 0.0% | 0.0% | 0.0% | 2.5% |
| gemini-2.5-flash | 2.0/5.0 | 60.0% | 0.0% | 0.0% | 0.0% | 10.0% |
| gpt-4o | 2.1/5.0 | 57.0% | 0.0% | 0.0% | 0.0% | 7.5% |
| gpt-4o-mini | 2.3/5.0 | 54.0% | 0.0% | 0.0% | 0.0% | 5.0% |
| llama-3.3-70b-instruct | 1.6/5.0 | 69.0% | 0.0% | 0.0% | 0.0% | 2.5% |
| mistral-large-2411 | 1.2/5.0 | 75.0% | 0.0% | 0.0% | 0.0% | 2.5% |
| qwen-2.5-72b-instruct | 1.6/5.0 | 68.5% | 0.0% | 0.0% | 0.0% | 0.0% |

## Analysis

Sequential BoK execution realizes 1.9 target queries on average vs. the maximum cap of 5, providing 61.2% theoretical savings. Most attacks succeed at Variant 1 (56.2%), showing that early variants capture most of the attack surface.

This supports the distinction between **maximum target-query cap** (matched between BoK-ST and PAIR-5 at K=5) and **realized target calls** (sequential BoK: 1.9, while PAIR-5 early-stops are not analyzed here but likely similar).