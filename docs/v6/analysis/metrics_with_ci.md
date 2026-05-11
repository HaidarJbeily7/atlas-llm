# Experiment Metrics with Confidence Intervals

Source: `docs/experiment/20260505_003630`

## ASR by Condition (pooled across models)

| Condition | N | Successes | ASR | 95% CI |
| --- | --- | --- | --- | --- |
| `adaptive_multi_turn` | 320 | 203 | 63.4% | [58.0%, 68.5%] |
| `adaptive_single_query_st` | 320 | 205 | 64.1% | [58.7%, 69.1%] |
| `adaptive_single_turn` | 320 | 272 | 85.0% | [80.7%, 88.5%] |
| `best_of_k_st` | 320 | 292 | 91.2% | [87.6%, 93.9%] |
| `direct_single_turn` | 320 | 51 | 15.9% | [12.3%, 20.3%] |
| `scripted_multi_turn` | 320 | 164 | 51.2% | [45.8%, 56.7%] |

## Cost & Latency by Condition

| Condition | Cost/attack (mean) | 95% CI | Latency/attack (median) | 95% CI |
| --- | --- | --- | --- | --- |
| `adaptive_multi_turn` | $0.0238 | [$0.0213, $0.0265] | 518430ms | [458078ms, 568591ms] |
| `adaptive_single_query_st` | $0.0068 | [$0.0057, $0.0083] | 181476ms | [167091ms, 198165ms] |
| `adaptive_single_turn` | $0.0138 | [$0.0115, $0.0165] | 284748ms | [268535ms, 313971ms] |
| `best_of_k_st` | $0.0179 | [$0.0144, $0.0219] | 573166ms | [513804ms, 706387ms] |
| `direct_single_turn` | $0.0017 | [$0.0009, $0.0030] | 17011ms | [16509ms, 17641ms] |
| `scripted_multi_turn` | $0.0104 | [$0.0079, $0.0134] | 117196ms | [106123ms, 129779ms] |

## ASR by Model x Condition

| Model | `adaptive_multi_turn` | `adaptive_single_query_st` | `adaptive_single_turn` | `best_of_k_st` | `direct_single_turn` | `scripted_multi_turn` |
| --- | --- | --- | --- | --- | --- | --- |
| claude-sonnet-4 | 20% [10%-35%] | 28% [16%-43%] | 42% [29%-58%] | 60% [45%-74%] | 12% [5%-26%] | 32% [20%-48%] |
| deepseek-chat-v3-0324 | 62% [47%-76%] | 88% [74%-95%] | 92% [80%-97%] | 98% [87%-100%] | 20% [10%-35%] | 57% [42%-71%] |
| gemini-2.5-flash | 70% [55%-82%] | 68% [52%-80%] | 92% [80%-97%] | 90% [77%-96%] | 20% [10%-35%] | 55% [40%-69%] |
| llama-3.3-70b-instruct | 62% [47%-76%] | 72% [57%-84%] | 90% [77%-96%] | 98% [87%-100%] | 12% [5%-26%] | 55% [40%-69%] |
| mistral-large-2411 | 72% [57%-84%] | 90% [77%-96%] | 95% [83%-99%] | 98% [87%-100%] | 48% [33%-63%] | 68% [52%-80%] |
| gpt-4o | 68% [52%-80%] | 57% [42%-71%] | 90% [77%-96%] | 92% [80%-97%] | 5% [1%-17%] | 38% [24%-53%] |
| gpt-4o-mini | 80% [65%-90%] | 48% [33%-63%] | 88% [74%-95%] | 95% [83%-99%] | 8% [3%-20%] | 38% [24%-53%] |
| qwen-2.5-72b-instruct | 72% [57%-84%] | 62% [47%-76%] | 90% [77%-96%] | 100% [91%-100%] | 2% [0%-13%] | 68% [52%-80%] |

## Paired Comparisons (McNemar, pooled)

| Comparison | ASR_A | ASR_B | Risk Diff | p-value | p (Bonferroni) | Discordant |
| --- | --- | --- | --- | --- | --- | --- |
| `adaptive_multi_turn` vs `adaptive_single_query_st` | 63.4% | 64.1% | +0.6% | 0.9285 | 1.0000 | 124 |
| `adaptive_multi_turn` vs `adaptive_single_turn` | 63.4% | 85.0% | +21.6% | 0.0000 | **0.0000** | 97 |
| `adaptive_multi_turn` vs `best_of_k_st` | 63.4% | 91.2% | +27.8% | 0.0000 | **0.0000** | 103 |
| `adaptive_multi_turn` vs `direct_single_turn` | 63.4% | 15.9% | -47.5% | 0.0000 | **0.0000** | 192 |
| `adaptive_multi_turn` vs `scripted_multi_turn` | 63.4% | 51.2% | -12.2% | 0.0009 | **0.0137** | 133 |
| `adaptive_single_query_st` vs `adaptive_single_turn` | 64.1% | 85.0% | +20.9% | 0.0000 | **0.0000** | 87 |
| `adaptive_single_query_st` vs `best_of_k_st` | 64.1% | 91.2% | +27.2% | 0.0000 | **0.0000** | 95 |
| `adaptive_single_query_st` vs `direct_single_turn` | 64.1% | 15.9% | -48.1% | 0.0000 | **0.0000** | 168 |
| `adaptive_single_query_st` vs `scripted_multi_turn` | 64.1% | 51.2% | -12.8% | 0.0003 | **0.0046** | 125 |
| `adaptive_single_turn` vs `best_of_k_st` | 85.0% | 91.2% | +6.2% | 0.0022 | **0.0333** | 40 |
| `adaptive_single_turn` vs `direct_single_turn` | 85.0% | 15.9% | -69.1% | 0.0000 | **0.0000** | 225 |
| `adaptive_single_turn` vs `scripted_multi_turn` | 85.0% | 51.2% | -33.8% | 0.0000 | **0.0000** | 130 |
| `best_of_k_st` vs `direct_single_turn` | 91.2% | 15.9% | -75.3% | 0.0000 | **0.0000** | 243 |
| `best_of_k_st` vs `scripted_multi_turn` | 91.2% | 51.2% | -40.0% | 0.0000 | **0.0000** | 140 |
| `direct_single_turn` vs `scripted_multi_turn` | 15.9% | 51.2% | +35.3% | 0.0000 | **0.0000** | 131 |
