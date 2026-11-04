import polars as pl

from halflife.score import label, scores


class Fake:
    def predict_proba(self, X):
        return __import__("numpy").c_[1 - X[:, 3] / 10, X[:, 3] / 10]

    def predict(self, X, pred_contrib):
        out = __import__("numpy").zeros((len(X), X.shape[1] + 1))
        out[:, 3], out[:, 4] = X[:, 3], -1
        return out


def test_scores_rank_coverage_and_drivers():
    from halflife.features import FEATURES

    rows = {f: [None, None] for f in FEATURES} | {"smart_5": [2, 7], "smart_9": [100, 100]}
    df = pl.DataFrame(
        rows | {"drive_id": ["a", "b"], "model": ["M", "M"], "date": ["2025-12-31"] * 2}
    )
    s = scores({"kind": "lightgbm", "model": Fake(), "models": {"M": 0}}, df, "f1", "v1")
    assert s["drive_id"].to_list() == ["b", "a"] and s["rank"].to_list() == [1, 2]
    assert s["coverage"].to_list() == [2 / 9, 2 / 9]
    assert s["top_drivers"].to_list()[0] == ["Reallocated sectors: 7"]


def test_labels_read_as_plain_language():
    assert label("smart_197_d30", 12, "M") == "Pending sectors changed by +12 in 30 days"
    assert label("age_days", 730, "M") == "Age: 2.0 years"
    assert label("smart_187_d7", None, "M") == "Uncorrectable errors not reported"
