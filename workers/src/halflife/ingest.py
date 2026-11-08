import hashlib
import os
import uuid
from datetime import date, timedelta
from pathlib import Path

import duckdb

from halflife import DATA

FIXTURE = Path(__file__).parents[2] / "tests" / "fixtures" / "onepct"


def connect() -> tuple[duckdb.DuckDBPyConnection, str]:
    """Return a DuckDB connection to B2 and an iceberg_scan() expression for Drive Stats."""
    e = os.environ
    con = duckdb.connect()
    con.execute("INSTALL httpfs; LOAD httpfs; INSTALL iceberg; LOAD iceberg;")
    con.execute("SET unsafe_enable_version_guessing = true")
    con.execute(
        f"CREATE SECRET b2 (TYPE s3, KEY_ID '{e['B2_KEY_ID']}', SECRET '{e['B2_APP_KEY']}', "
        f"REGION '{e['B2_REGION']}', ENDPOINT '{e['B2_ENDPOINT']}')"
    )
    path = f"s3://{e['B2_BUCKET']}/{e['B2_PREFIX']}"
    return con, f"iceberg_scan('{path}', version = '?', allow_moved_paths = true)"


def sampled(pct: float) -> str:
    """SQL predicate keeping a stable pct% of drives (nested: 1% is a subset of 10%)."""
    return f"md5_number_lower(serial_number) % 10000 < {round(pct * 100)}"


def ingest_month(con, src: str, lo: date, hi: date, pct: float, run_id: str) -> int:
    """Write one month of sampled rows to bronze (and the 1% fixture), replacing it."""
    con.execute(
        f"CREATE OR REPLACE TEMP TABLE m AS SELECT * FROM {src} "
        f"WHERE date BETWEEN DATE '{lo}' AND DATE '{hi}' AND {sampled(pct)}"
    )
    counts = con.execute("SELECT count(COLUMNS(*)) FROM m").fetchall()[0]
    present = [c for c, n in zip(con.table("m").columns, counts) if n]
    schema_hash = hashlib.md5(",".join(sorted(present)).encode()).hexdigest()[:12]
    part = f"year={lo.year}/month={lo.month:02d}"
    for root, where in [(DATA / "bronze", "true"), (FIXTURE / "bronze", sampled(min(pct, 1)))]:
        (root / part).mkdir(parents=True, exist_ok=True)
        con.execute(
            f"COPY (SELECT *, '{run_id}' AS _run_id, '{schema_hash}' AS _schema_hash "
            f"FROM m WHERE {where}) TO '{root / part / 'data.parquet'}'"
        )
    return con.execute("SELECT count(*) FROM m").fetchall()[0][0]


def ingest(start: date, end: date, pct: float) -> None:
    """Ingest every whole month touching [start, end]; each month's partition is replaced."""
    con, src = connect()
    run_id = uuid.uuid4().hex[:12]
    lo = start.replace(day=1)
    while lo <= end:
        next_month = (lo + timedelta(days=32)).replace(day=1)
        hi = next_month - timedelta(days=1)
        print(f"{lo:%Y-%m}: {ingest_month(con, src, lo, hi, pct, run_id):,} rows")
        lo = next_month


def resume_from(bronze: Path, default: date) -> date:
    """First day of the newest ingested month (re-ingested, as it may have grown), else default."""
    months = sorted(bronze.glob("year=*/month=*"))
    if not months:
        return default
    year, month = (int(part.split("=")[1]) for part in months[-1].parts[-2:])
    return date(year, month, 1)


def newest_day(start: date) -> date:
    """Latest date published in the Drive Stats table, reading only months from start on."""
    con, src = connect()
    return con.execute(f"SELECT max(date) FROM {src} WHERE date >= DATE '{start}'").fetchall()[0][0]
