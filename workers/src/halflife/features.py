from pathlib import Path

import duckdb

from halflife.clean import ATTRS

DELTAS = [a for a in ATTRS if a not in (9, 194)]
FEATURES = (
    ["capacity_tb", "age_days", "temp_mean_7d"]
    + [f"smart_{a}" for a in ATTRS]
    + [f"smart_{a}_d{n}" for a in DELTAS for n in (7, 30)]
)


def features(silver: Path, gold: Path, horizon: int) -> int:
    """Silver -> gold: one row per drive-day with past-only features and label y."""
    gold.mkdir(parents=True, exist_ok=True)
    deltas = ", ".join(
        f"smart_{a} - first_value(smart_{a}) OVER w{n} AS smart_{a}_d{n}"
        for a in DELTAS
        for n in (7, 30)
    )
    frame = "PARTITION BY drive_id ORDER BY date RANGE BETWEEN INTERVAL {} DAYS PRECEDING AND CURRENT ROW"
    con = duckdb.connect()
    con.execute("SET preserve_insertion_order = false")
    con.execute(f"""COPY (
        SELECT d.drive_id, d.date, d.model, d.manufacturer, d.capacity_tb,
          d.smart_9 / 24.0 AS age_days, avg(d.smart_194) OVER w7 AS temp_mean_7d,
          {", ".join(f"d.smart_{a}" for a in ATTRS)}, {deltas},
          CASE WHEN d.date > max(d.date) OVER () - {horizon} THEN NULL
               ELSE coalesce(l.failure_date - d.date < {horizon}, false) END AS y
        FROM '{silver}/drive_days.parquet' d JOIN '{silver}/lifecycle.parquet' l USING (drive_id)
        WINDOW w7 AS ({frame.format(7)}), w30 AS ({frame.format(30)})
    ) TO '{gold}/features.parquet'""")
    return con.execute(f"SELECT count(*) FROM '{gold}/features.parquet'").fetchall()[0][0]
