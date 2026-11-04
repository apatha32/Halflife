import polars as pl

from halflife.evaluate import cost_curve, metrics


def test_precision_recall_at_k_per_snapshot():
    s = pl.DataFrame(
        {
            "drive_id": list("abcdabcd"),
            "date": ["2025-01-06"] * 4 + ["2025-01-13"] * 4,
            "y": [True, False, True, False, False, False, False, True],
            "score": [0.9, 0.8, 0.1, 0.0, 0.9, 0.8, 0.7, 0.6],
        }
    )
    m = metrics(s, k=2)
    assert m["precision_at_2"] == 0.25 and m["recall_at_2"] == round(1 / 3, 4)
    assert cost_curve(s)[-1] == {"k_pct": 1.0, "failures_avoided": 0.5, "healthy_pulled": 0.5}
