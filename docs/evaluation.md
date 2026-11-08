# Evaluation: model 20261108-1541

Best 30-day ranker (by validation PR-AUC): **lightgbm**. K = 50 drives per weekly snapshot.
Splits: {'train': ['2024-01-01', '2025-07-01'], 'validate': ['2025-08-01', '2026-01-29'], 'test': ['2026-03-01', '2026-08-31']}.

## Ranking (raw scores, 30-day label)

### Validate

| model | pr_auc | precision_at_50 | recall_at_50 |
|---|---|---|---|
| naive_rule | 0.0191 | 0.0338 | 0.0541 |
| logistic | 0.0571 | 0.1062 | 0.1697 |
| lightgbm | 0.0722 | 0.1185 | 0.1894 |

### Test

| model | pr_auc | precision_at_50 | recall_at_50 |
|---|---|---|---|
| naive_rule | 0.0524 | 0.077 | 0.1025 |
| logistic | 0.1007 | 0.1481 | 0.197 |
| lightgbm | 0.1048 | 0.1593 | 0.2118 |

## Calibrated chance of failing within 7, 30 and 90 days (test)

Each head is Platt-calibrated on the validation period. Brier is the mean squared error of the
probability; expected vs observed compares summed probabilities with actual failures.

| model | pr_auc | precision_at_50 | recall_at_50 | brier | expected_failures | observed_failures |
|---|---|---|---|---|---|---|
| 7d | 0.0616 | 0.0593 | 0.3279 | 0.000247 | 219.5 | 244 |
| 30d | 0.1048 | 0.1593 | 0.2118 | 0.000995 | 900.3 | 1015 |
| 90d | 0.1568 | 0.3433 | 0.1453 | 0.003048 | 1876.1 | 2126 |

### 30-day calibration by predicted decile (test)

| Decile | Mean predicted | Observed rate |
|---|---|---|
| 1 | 0.0001 | 0.0004 |
| 2 | 0.0001 | 0.0003 |
| 3 | 0.0002 | 0.0002 |
| 4 | 0.0002 | 0.0003 |
| 5 | 0.0003 | 0.0003 |
| 6 | 0.0004 | 0.0003 |
| 7 | 0.0005 | 0.0003 |
| 8 | 0.0006 | 0.0002 |
| 9 | 0.0009 | 0.0005 |
| 10 | 0.0062 | 0.0080 |

![Cost curve](../models/20261108-1541/cost_curve.png)
