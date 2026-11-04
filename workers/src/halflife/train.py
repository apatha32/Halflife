import json
from datetime import datetime, timedelta
from pathlib import Path

import duckdb
import joblib
import numpy as np
import polars as pl
from lightgbm import LGBMClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import FunctionTransformer, StandardScaler

from halflife import evaluate
from halflife.features import FEATURES

GAP = 30


def splits(gold: Path) -> dict[str, tuple]:
    """Train/validate/test date ranges (60/20/20 of labeled days) with 30-day gaps."""
    lo, hi = duckdb.sql(
        f"SELECT min(date), max(date) FROM '{gold}' WHERE y IS NOT NULL"
    ).fetchall()[0]
    span = (hi - lo).days - 2 * GAP
    t_end = lo + timedelta(int(span * 0.6))
    v_end = t_end + timedelta(GAP + int(span * 0.2))
    return {
        "train": (lo, t_end),
        "validate": (t_end + timedelta(GAP + 1), v_end),
        "test": (v_end + timedelta(GAP + 1), hi),
    }


def load(gold: Path, span: tuple, where: str) -> pl.DataFrame:
    """Labeled gold rows in a date span matching an extra SQL filter."""
    return duckdb.sql(f"""SELECT drive_id, date, model, {", ".join(FEATURES)}, y FROM '{gold}'
        WHERE y IS NOT NULL AND date BETWEEN '{span[0]}' AND '{span[1]}' AND {where}""").pl()


def matrix(df: pl.DataFrame, models: dict[str, int]) -> np.ndarray:
    """Feature matrix: FEATURES as floats plus the drive model as a category code."""
    code = pl.col("model").replace_strict(models, default=None, return_dtype=pl.Float64)
    return df.select(pl.col(FEATURES).cast(pl.Float64), code).to_numpy()


def naive(df: pl.DataFrame) -> np.ndarray:
    """Naive rule score: reallocated + pending sectors (> 0 means pull)."""
    return (
        df.select(pl.col("smart_5").fill_null(0) + pl.col("smart_197").fill_null(0))
        .to_numpy()
        .ravel()
    )


def fit(tr: pl.DataFrame) -> dict[str, dict]:
    """Fit logistic regression and LightGBM; return {name: artifact}."""
    models = {m: i for i, m in enumerate(sorted(tr["model"].unique().drop_nulls()))}
    lr = make_pipeline(
        FunctionTransformer(np.arcsinh),
        SimpleImputer(strategy="median", keep_empty_features=True),
        StandardScaler(),
        LogisticRegression(class_weight="balanced", max_iter=2000),
    )
    gbm = LGBMClassifier(n_estimators=300, learning_rate=0.05, class_weight="balanced", verbose=-1)
    X, y = matrix(tr, models), tr["y"].to_numpy()
    lr.fit(X[:, :-1], y)
    gbm.fit(X, y, categorical_feature=[X.shape[1] - 1])
    return {
        n: {"kind": n, "model": m, "models": models}
        for n, m in [("logistic", lr), ("lightgbm", gbm)]
    }


def predict(art: dict, df: pl.DataFrame) -> np.ndarray:
    """Failure probability for each row from a saved artifact."""
    X = matrix(df, art["models"])
    return art["model"].predict_proba(X if art["kind"] == "lightgbm" else X[:, :-1])[:, 1]


def save(out: Path, art: dict, meta: dict, curves: dict) -> None:
    """Write model.pkl, metrics.json, cost_curve.json/png to out/."""
    out.mkdir(parents=True)
    joblib.dump(art, out / "model.pkl")
    (out / "metrics.json").write_text(json.dumps(meta, indent=2))
    (out / "cost_curve.json").write_text(json.dumps(curves, indent=2))
    evaluate.plot(curves, out / "cost_curve.png")


def train(gold: Path, out: Path, k: int, neg_rate: float) -> dict:
    """Fit naive/logistic/LightGBM, evaluate on weekly snapshots, save the best model."""
    gold, results, curves = gold / "features.parquet", {}, {}
    span = splits(gold)
    keep = f"(y OR md5_number_lower(drive_id || date) % 10000 < {round(neg_rate * 10000)})"
    tr = load(gold, span["train"], keep)
    arts = fit(tr)
    scorers = {"naive_rule": naive} | {n: (lambda d, a=a: predict(a, d)) for n, a in arts.items()}
    for split in ("validate", "test"):
        df = load(gold, span[split], "isodow(date) = 1")
        for name, score in scorers.items():
            s = df.select("drive_id", "date", "y").with_columns(score=score(df))
            results.setdefault(split, {})[name] = evaluate.metrics(s, k)
            if split == "test":
                curves[name] = evaluate.cost_curve(s)
    best = max(arts, key=lambda m: results["validate"][m]["pr_auc"])
    version = datetime.now().strftime("%Y%m%d-%H%M")
    meta = {
        "version": version,
        "best": best,
        "k": k,
        "neg_rate": neg_rate,
        "train_rows": len(tr),
        "splits": {s: [str(a), str(b)] for s, (a, b) in span.items()},
        "features": FEATURES + ["model"],
        "results": results,
    }
    save(out / version, arts[best], meta, curves)
    return meta
