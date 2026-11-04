import json
import os
from datetime import date
from pathlib import Path

import duckdb
import httpx
import joblib
import numpy as np
import polars as pl

from halflife.clean import ATTRS
from halflife.features import FEATURES
from halflife.train import matrix, predict

HISTORY_DRIVES = 1000
NAMES = {
    5: "Reallocated sectors",
    9: "Power-on hours",
    12: "Power cycles",
    187: "Uncorrectable errors",
    188: "Command timeouts",
    194: "Temperature (°C)",
    197: "Pending sectors",
    198: "Offline uncorrectable sectors",
    199: "Cable CRC errors",
}


def label(feature: str, value, model: str) -> str:
    """Plain-language label for one feature value."""
    attr, _, days = feature.removeprefix("smart_").partition("_d")
    if value is None and feature != "model":
        name = NAMES[int(attr)] if attr.isdigit() else feature.replace("_", " ").capitalize()
        return f"{name} not reported"
    if feature == "model":
        return f"Drive model {model} has a higher failure history"
    if feature == "age_days":
        return f"Age: {value / 365:.1f} years"
    if feature == "capacity_tb":
        return f"Capacity: {value:g} TB"
    if feature == "temp_mean_7d":
        return f"7-day average temperature: {value:.0f} °C"
    if days:
        return f"{NAMES[int(attr)]} changed by {value:+,.0f} in {days} days"
    return f"{NAMES[int(attr)]}: {value:,.0f}"


def contributions(art: dict, df: pl.DataFrame) -> np.ndarray:
    """Per-feature contributions to risk (SHAP for LightGBM, coef * x for logistic)."""
    X = matrix(df, art["models"])
    if art["kind"] == "lightgbm":
        return art["model"].predict(X, pred_contrib=True)[:, :-1]
    return art["model"][:-1].transform(X[:, :-1]) * art["model"][-1].coef_[0]


def drivers(art: dict, df: pl.DataFrame) -> list[list[str]]:
    """Top 3 risk-raising features per row as labels."""
    names, c = FEATURES + ["model"], contributions(art, df)
    rows = df.select(*FEATURES, "model").rows()
    return [
        [label(names[j], row[j], row[-1]) for j in np.argsort(-ci)[:3] if ci[j] > 0]
        for ci, row in zip(c, rows)
    ]


def rest(path: str) -> tuple[str, dict]:
    """Supabase REST URL and service-role headers."""
    key = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
    return f"{os.environ['SUPABASE_URL']}/rest/v1/{path}", {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Prefer": "resolution=merge-duplicates,return=minimal",
    }


def upsert(table: str, rows: list[dict], conflict: str) -> None:
    """Upsert rows to Supabase in batches with the service-role key."""
    url, headers = rest(f"{table}?on_conflict={conflict}")
    for i in range(0, len(rows), 1000):
        httpx.post(url, json=rows[i : i + 1000], headers=headers, timeout=120).raise_for_status()


def fleet_id(name: str) -> str:
    """Look up a fleet's id by name."""
    url, headers = rest("fleets")
    r = httpx.get(url, params={"name": f"eq.{name}", "select": "id"}, headers=headers)
    return r.raise_for_status().json()[0]["id"]


def scores(art: dict, df: pl.DataFrame, fid: str, version: str) -> pl.DataFrame:
    """Risk, rank, coverage and top drivers for every drive in df (one day)."""
    smart = [f"smart_{a}" for a in ATTRS]
    return (
        df.with_columns(risk=predict(art, df), top_drivers=pl.Series(drivers(art, df)))
        .with_columns(
            rank=pl.col("risk").rank("ordinal", descending=True).cast(pl.Int32),
            coverage=pl.sum_horizontal(pl.col(smart).is_not_null()) / len(smart),
            fleet_id=pl.lit(fid),
            model_version=pl.lit(version),
            score_date=pl.col("date").cast(pl.String),
        )
        .sort("rank")
    )


def history(data: Path, fid: str, day: date, drive_ids: list[str]) -> list[dict]:
    """Last 180 days of charted SMART values for the given drives."""
    return (
        duckdb.sql(
            f"""SELECT '{fid}' AS fleet_id, drive_id, date::VARCHAR AS date, smart_5, smart_187,
        smart_197, smart_198, smart_194 FROM '{data}/silver/drive_days.parquet'
        WHERE list_contains(?, drive_id) AND date BETWEEN DATE '{day}' - 179 AND DATE '{day}'""",
            params=[drive_ids],
        )
        .pl()
        .to_dicts()
    )


def score(day: date, fleet: str, data: Path, model_dir: Path) -> int:
    """Score drives active on `day` and upsert drives, scores, history and quality report."""
    art = joblib.load(model_dir / "model.pkl")
    df = duckdb.sql(f"SELECT * FROM '{data}/gold/features.parquet' WHERE date = '{day}'").pl()
    fid = fleet_id(fleet)
    s = scores(art, df, fid, model_dir.name)
    drives = s.select("fleet_id", "drive_id", "model", "manufacturer", "capacity_tb")
    upsert("drives", drives.to_dicts(), "fleet_id,drive_id")
    cols = ["fleet_id", "drive_id", "score_date", "risk", "rank", "age_days", "coverage"]
    rows = s.select(*cols, "top_drivers", "model_version").fill_nan(None).to_dicts()
    upsert("drive_scores", rows, "fleet_id,drive_id,score_date")
    top = s["drive_id"].head(HISTORY_DRIVES).to_list()
    upsert("drive_history", history(data, fid, day, top), "fleet_id,drive_id,date")
    r = json.loads(max((data / "reports").glob("*.json")).read_text())
    upsert(
        "quality_reports",
        [{"fleet_id": fid, "run_at": r["run_at"], "report": r}],
        "fleet_id,run_at",
    )
    return len(s)
