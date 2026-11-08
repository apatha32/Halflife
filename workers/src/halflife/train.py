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
from halflife.features import FEATURES, HORIZONS

GAP = 30
PRIMARY = 30


def splits(gold: Path) -> dict[str, tuple]:
    """Train/validate/test date ranges (60/20/20 of labeled days) with 30-day gaps."""
    lo, hi = duckdb.sql(
        f"SELECT min(date), max(date) FROM '{gold}' WHERE y_{PRIMARY} IS NOT NULL"
    ).fetchall()[0]
    span = (hi - lo).days - 2 * GAP
    t_end = lo + timedelta(int(span * 0.6))
    v_end = t_end + timedelta(GAP + int(span * 0.2))
    return {
        "train": (lo, t_end),
        "validate": (t_end + timedelta(GAP + 1), v_end),
        "test": (v_end + timedelta(GAP + 1), hi),
    }


def load(gold: Path, span: tuple, where: str, h: int = PRIMARY) -> pl.DataFrame:
    """Gold rows labeled for horizon h in a date span matching an extra SQL filter; y = y_h."""
    return duckdb.sql(f"""SELECT drive_id, date, model, {", ".join(FEATURES)}, y_{h} AS y
        FROM '{gold}' WHERE y_{h} IS NOT NULL AND date BETWEEN '{span[0]}' AND '{span[1]}'
        AND {where}""").pl()


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


def lightgbm(tr: pl.DataFrame, models: dict[str, int]) -> LGBMClassifier:
    """LightGBM with class weights; drive model as a categorical feature."""
    gbm = LGBMClassifier(n_estimators=300, learning_rate=0.05, class_weight="balanced", verbose=-1)
    X = matrix(tr, models)
    return gbm.fit(X, tr["y"].to_numpy(), categorical_feature=[X.shape[1] - 1])


def fit(tr: pl.DataFrame) -> tuple[dict[str, int], dict[str, dict]]:
    """Fit logistic regression and LightGBM; return (model codes, {name: head})."""
    models = {m: i for i, m in enumerate(sorted(tr["model"].unique().drop_nulls()))}
    lr = make_pipeline(
        FunctionTransformer(np.arcsinh),
        SimpleImputer(strategy="median", keep_empty_features=True),
        StandardScaler(),
        LogisticRegression(class_weight="balanced", max_iter=2000),
    )
    lr.fit(matrix(tr, models)[:, :-1], tr["y"].to_numpy())
    heads = {"logistic": {"kind": "logistic", "model": lr}}
    heads["lightgbm"] = {"kind": "lightgbm", "model": lightgbm(tr, models)}
    return models, heads


def raw(head: dict, X: np.ndarray) -> np.ndarray:
    """Uncalibrated score of a head (ranking only)."""
    return head["model"].predict_proba(X if head["kind"] == "lightgbm" else X[:, :-1])[:, 1]


def logit(p: np.ndarray) -> np.ndarray:
    p = np.clip(p, 1e-6, 1 - 1e-6)
    return np.log(p / (1 - p))


def calibrate(p: np.ndarray, y: np.ndarray) -> tuple[float, float]:
    """Platt scaling: fit sigmoid(a * logit(p) + b) to observed outcomes (rank-preserving)."""
    m = LogisticRegression(C=1e6).fit(logit(p).reshape(-1, 1), y)
    return float(m.coef_[0][0]), float(m.intercept_[0])


def predict(art: dict, df: pl.DataFrame, h: int = PRIMARY) -> np.ndarray:
    """Calibrated probability of failing within h days for each row."""
    head = art["heads"][h]
    z = head["a"] * logit(raw(head, matrix(df, art["models"]))) + head["b"]
    return 1 / (1 + np.exp(-z))


def save(out: Path, art: dict, meta: dict, curves: dict) -> None:
    """Write model.pkl, metrics.json, cost_curve.json/png to out/."""
    out.mkdir(parents=True)
    joblib.dump(art, out / "model.pkl")
    (out / "metrics.json").write_text(json.dumps(meta, indent=2))
    (out / "cost_curve.json").write_text(json.dumps(curves, indent=2))
    evaluate.plot(curves, out / "cost_curve.png")


def compare(gold: Path, span: dict, models: dict, heads: dict, k: int) -> tuple[dict, dict]:
    """Rank metrics for naive/logistic/LightGBM on weekly snapshots, plus test cost curves."""
    results, curves = {}, {}
    scorers = {"naive_rule": naive} | {
        n: (lambda d, hd=hd: raw(hd, matrix(d, models))) for n, hd in heads.items()
    }
    for split in ("validate", "test"):
        df = load(gold, span[split], "isodow(date) = 1")
        for name, score in scorers.items():
            s = df.select("drive_id", "date", "y").with_columns(score=score(df))
            results.setdefault(split, {})[name] = evaluate.metrics(s, k)
            if split == "test":
                curves[name] = evaluate.cost_curve(s)
    return results, curves


def horizons(gold: Path, span: dict, art: dict, keep: str, k: int) -> dict:
    """Fit 7/90-day heads, calibrate every head on validation, evaluate calibrated test scores.

    `keep` is the negative-downsampling filter with an `{h}` placeholder for the horizon.
    """
    report = {}
    for h in HORIZONS:
        if h != PRIMARY:
            tr = load(gold, span["train"], keep.format(h=h), h)
            art["heads"][h] = {"kind": "lightgbm", "model": lightgbm(tr, art["models"])}
        head, val = art["heads"][h], load(gold, span["validate"], "isodow(date) = 1", h)
        head["a"], head["b"] = calibrate(raw(head, matrix(val, art["models"])), val["y"].to_numpy())
        test = load(gold, span["test"], "isodow(date) = 1", h)
        p = predict(art, test, h)
        s = test.select("drive_id", "date", "y").with_columns(score=p)
        report[f"{h}d"] = evaluate.metrics(s, k) | evaluate.calibration(test["y"].to_numpy(), p)
    return report


def train(gold: Path, out: Path, k: int, neg_rate: float) -> dict:
    """Pick the best 30-day model, add calibrated 7/30/90-day heads, save with a drift reference."""
    gold = gold / "features.parquet"
    span = splits(gold)
    keep = f"(y_{{h}} OR md5_number_lower(drive_id || date) % 10000 < {round(neg_rate * 10000)})"
    tr = load(gold, span["train"], keep.format(h=PRIMARY))
    models, heads = fit(tr)
    results, curves = compare(gold, span, models, heads, k)
    best = max(heads, key=lambda m: results["validate"][m]["pr_auc"])
    art = {"models": models, "heads": {PRIMARY: heads[best]}}
    calibrated = horizons(gold, span, art, keep, k)
    art["reference"] = evaluate.reference(load(gold, span["train"], "isodow(date) = 1"), FEATURES)
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
        "calibrated_test": calibrated,
    }
    save(out / version, art, meta, curves)
    return meta
