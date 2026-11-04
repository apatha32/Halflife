from pathlib import Path

import duckdb

from halflife import report

ATTRS = [5, 9, 12, 187, 188, 194, 197, 198, 199]
COUNTERS = [5, 9, 12, 187, 188, 198, 199]
MAKERS = {
    "TOSHIBA": "Toshiba",
    "HGST": "HGST",
    "WDC": "WDC",
    "WUH": "WDC",
    "WD ": "WDC",
    "ST": "Seagate",
    "Seagate": "Seagate",
    "CT": "Crucial",
    "MTFD": "Micron",
    "Samsung": "Samsung",
    "DELLBOSS": "Dell",
}
MANUFACTURER = (
    "CASE "
    + " ".join(f"WHEN starts_with(model, '{p}') THEN '{m}'" for p, m in MAKERS.items())
    + " ELSE 'Other' END"
)
RAW = ", ".join(f"smart_{a}_raw" for a in ATTRS)
REASON = f"""CASE
  WHEN serial_number IS NULL OR date IS NULL THEN 'missing_key'
  WHEN row_number() OVER (PARTITION BY serial_number, date ORDER BY failure DESC, capacity_bytes DESC) > 1
    THEN 'duplicate'
  WHEN date > min(date) FILTER (failure = 1) OVER (PARTITION BY serial_number)
    THEN 'after_failure'
  WHEN capacity_bytes <= 0 THEN 'bad_capacity'
  WHEN smart_194_raw NOT BETWEEN 1 AND 100 THEN 'bad_temperature'
  WHEN smart_9_raw > 24 * 365 * 20 THEN 'bad_power_on_hours'
  WHEN least({RAW}) < 0 THEN 'negative_smart'
END"""


def clean(bronze: Path, silver: Path) -> duckdb.DuckDBPyConnection:
    """Bronze -> silver drive_days, lifecycle and quarantine; returns the connection."""
    silver.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect()
    con.execute("SET preserve_insertion_order = false")
    con.execute(f"""CREATE TABLE tagged AS SELECT serial_number, date, model, capacity_bytes,
        failure, {RAW}, _schema_hash, {REASON} AS reason
        FROM read_parquet('{bronze}/**/*.parquet', union_by_name = true)""")
    drops = ", ".join(
        f"greatest(lag(smart_{c}_raw) OVER w - smart_{c}_raw, 0) AS drop_{c}" for c in COUNTERS
    )
    smart = ", ".join(
        f"(smart_{a}_raw + coalesce(sum(drop_{a}) OVER w, 0))::BIGINT AS smart_{a}"
        if a in COUNTERS
        else f"smart_{a}_raw AS smart_{a}"
        for a in ATTRS
    )
    total_drop = " + ".join(f"drop_{c}" for c in COUNTERS)
    con.execute(f"""CREATE TABLE drive_days AS
        WITH d AS (SELECT *, {drops} FROM tagged WHERE reason IS NULL
                   WINDOW w AS (PARTITION BY serial_number ORDER BY date))
        SELECT serial_number AS drive_id, date, model, {MANUFACTURER} AS manufacturer,
          capacity_bytes / 1e12 AS capacity_tb, failure, {smart},
          ({total_drop}) > 0 AS reset_event,
          sum({total_drop}) OVER w > 0 AS rebased, _schema_hash
        FROM d WINDOW w AS (PARTITION BY serial_number ORDER BY date
                            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW)""")
    con.execute("""CREATE TABLE lifecycle AS SELECT drive_id, any_value(model) AS model,
        min(date) AS first_seen, max(date) AS last_seen, bool_or(failure = 1) AS failed,
        min(date) FILTER (failure = 1) AS failure_date,
        CASE WHEN bool_or(failure = 1) THEN 'failed'
             WHEN max(date) = (SELECT max(date) FROM drive_days) THEN 'still_active'
             ELSE 'retired_or_missing' END AS end_reason
        FROM drive_days GROUP BY drive_id""")
    con.execute("CREATE TABLE quarantine AS SELECT * FROM tagged WHERE reason IS NOT NULL")
    for name in ["drive_days", "lifecycle", "quarantine"]:
        con.execute(f"COPY {name} TO '{silver / name}.parquet'")
    return con


def run(data: Path) -> tuple[dict, dict]:
    """Clean data/bronze into data/silver and save the quality report to data/reports."""
    return report.save(clean(data / "bronze", data / "silver"), data / "reports")
