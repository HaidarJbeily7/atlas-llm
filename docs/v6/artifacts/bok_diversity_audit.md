# BoK Strategy Diversity Audit

## Overall Statistics

- **Total intents**: 40
- **Total variants**: 200
- **Average variants per intent**: 5.0
- **Low diversity intents**: 2 (5.0%)
- **High similarity intents**: 0 (0.0%)

## Strategy Family Distribution

| Strategy Family | Count | Percentage |
|-----------------|-------|------------|
| Security Exercise | 34 | 17.0% |
| Academic | 26 | 13.0% |
| Fiction | 23 | 11.5% |
| Role Play | 22 | 11.0% |
| Step By Step | 18 | 9.0% |
| Translation | 18 | 9.0% |
| Other | 16 | 8.0% |
| Historical | 14 | 7.0% |
| Hypothetical | 13 | 6.5% |
| Educational | 8 | 4.0% |
| Technical | 5 | 2.5% |
| Prompt Injection | 3 | 1.5% |

## Flagged Intents (Low Diversity or High Similarity)

| Intent ID | Unique Strategies | Max Similarity | Flags |
|-----------|-------------------|----------------|-------|
| intent-hacking-exploit | 1/5 | 0.098 | low_strategy_diversity (1/5) |
| intent-multilingual-injection | 1/5 | 0.086 | low_strategy_diversity (1/5) |

## Sample Intent Analysis

### intent-weapons-synthesis

- **Unique strategies**: 4/5
- **Strategy breakdown**: fiction=2, hypothetical=1, historical=1, educational=1
- **Max similarity**: 0.075
- **Mean similarity**: 0.045

### intent-hacking-exploit

- **Unique strategies**: 1/5
- **Strategy breakdown**: security_exercise=5
- **Max similarity**: 0.098
- **Mean similarity**: 0.037
- **Flags**: low_strategy_diversity (1/5)

### intent-drug-synthesis

- **Unique strategies**: 4/5
- **Strategy breakdown**: academic=2, step_by_step=1, historical=1, role_play=1
- **Max similarity**: 0.122
- **Mean similarity**: 0.053

## Analysis

✅ **Strategy diversity is good**: Only 5.0% of intents have < 3 unique strategies.
✅ **Textual diversity is good**: Only 0.0% of intents have high similarity (>0.7).
✅ **Strategy balance is good**: Most common strategy (security_exercise) is 17.0% of variants.
