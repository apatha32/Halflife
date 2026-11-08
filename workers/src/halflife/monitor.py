import duckdb
import joblib

from halflife.evaluate import calibration, metrics, psi
from halflife.train import predict


def health(gold, model_dir, k: int) -> dict:
    """Drift of the newest day versus training, and a backtest on the latest fully labeled Monday."""
    art, src = joblib.load(model_dir / "model.pkl"), f"'{gold}/features.parquet'"
    newest = duckdb.sql(f"SELECT * FROM {src} WHERE date = (SELECT max(date) FROM {src})").pl()
    drift = psi(art["reference"], newest)
    day = duckdb.sql(
        f"SELECT max(date) FROM {src} WHERE y_30 IS NOT NULL AND isodow(date) = 1"
    ).fetchall()[0][0]
    snap = duckdb.sql(f"SELECT *, y_30 AS y FROM {src} WHERE date = '{day}'").pl()
    p = predict(art, snap)
    s = snap.select("drive_id", "date", "y").with_columns(score=p)
    cal = calibration(snap["y"].to_numpy(), p)
    return {
        "model_version": model_dir.name,
        "drift_date": str(newest["date"][0]),
        "drift_psi": dict(sorted(drift.items(), key=lambda kv: -kv[1])[:8]),
        "backtest_date": str(day),
        "backtest": metrics(s, k)
        | {k2: cal[k2] for k2 in ("expected_failures", "observed_failures")},
    }
