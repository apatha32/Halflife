import hashlib
import json
import math
import re
import uuid
from datetime import date
from difflib import SequenceMatcher
from pathlib import Path

import duckdb
import yaml

from halflife import clean
from halflife.clean import ATTRS
from halflife.features import features
from halflife.score import score

DATE_FORMATS = ["%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y"]
# target -> (name aliases, value check on the column profile)
TARGETS = {
    "drive_id": (
        ["serial number", "serial no", "serial", "sn", "drive id", "device serial"],
        lambda p: p["num"] < 0.5 and p["distinct"] > 10,
    ),
    "date": (["date", "reading date", "day", "timestamp", "collected"], lambda p: p["date"] > 0.9),
    "model": (
        ["model", "drive model", "device model"],
        lambda p: p["num"] < 0.5 and p["distinct"] < 500,
    ),
    "capacity_tb": (
        ["capacity tb", "size tb", "capacity", "user capacity", "capacity bytes"],
        lambda p: p["num"] > 0.9 and (0.1 <= p["med"] <= 40 or 1e11 <= p["med"] <= 5e13),
    ),
    "failure": (
        ["failure", "failed", "is failed"],
        lambda p: p["num"] > 0.9 and p["min"] >= 0 and p["max"] <= 1,
    ),
    "smart_5": (
        ["reallocated sectors", "reallocated sector ct", "realloc sector ct"],
        lambda p: p["min"] >= 0,
    ),
    "smart_9": (["power on hours", "power on hrs"], lambda p: 500 <= p["med"] <= 150_000),
    "smart_12": (["power cycle count"], lambda p: p["min"] >= 0),
    "smart_187": (
        ["reported uncorrect", "reported uncorrectable", "uncorrectable errors"],
        lambda p: p["min"] >= 0,
    ),
    "smart_188": (["command timeout"], lambda p: p["min"] >= 0),
    "smart_194": (
        ["temperature", "temp", "temperature celsius"],
        lambda p: 15 <= p["med"] <= 60 or 80 <= p["med"] <= 130,
    ),
    "smart_197": (["pending sectors", "current pending sector"], lambda p: p["min"] >= 0),
    "smart_198": (["offline uncorrectable"], lambda p: p["min"] >= 0),
    "smart_199": (
        ["crc error count", "udma crc error count", "udma crc errors"],
        lambda p: p["min"] >= 0,
    ),
}
NUM = "try_cast(replace({c}, ',', '') AS DOUBLE)"
TRANSFORMS = {"fahrenheit_to_celsius": "({v} - 32) * 5 / 9", "bytes_to_tb": "{v} / 1e12"}


def ident(name: str) -> str:
    """Quote a customer-supplied column name as a SQL identifier."""
    return '"' + name.replace('"', '""') + '"'


def norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()


def profile(file: Path) -> dict[str, dict]:
    """Per-column numeric rate, range, distinct count and best date format."""
    con = duckdb.connect()
    con.execute(f"CREATE TABLE f AS SELECT * FROM read_csv('{file}', all_varchar = true)")
    out = {}
    for c in con.table("f").columns:
        q = ident(c)
        n = NUM.format(c=q)
        dates = ", ".join(f"count(try_strptime({q}, '{f}')) / count({q})" for f in DATE_FORMATS)
        row = con.execute(f"""SELECT count({n}) / count({q}), min({n}), median({n}), max({n}),
            count(DISTINCT {q}), {dates} FROM f""").fetchall()[0]
        best = max(range(len(DATE_FORMATS)), key=lambda i: row[5 + i] or 0)
        nums = [math.nan if v is None else v for v in row[1:4]]
        out[c] = {
            "num": row[0] or 0,
            "min": nums[0],
            "med": nums[1],
            "max": nums[2],
            "distinct": row[4],
            "date": row[5 + best] or 0,
            "date_format": DATE_FORMATS[best],
        }
    return out


def propose(prof: dict[str, dict]) -> dict:
    """Match columns to targets by 0.6 * name similarity + 0.4 * value check, greedily."""

    def score(t, c):
        name = max(SequenceMatcher(None, norm(c), a).ratio() for a in TARGETS[t][0] + [norm(t)])
        return round(0.6 * name + 0.4 * bool(TARGETS[t][1](prof[c])), 2)

    pairs = sorted(((score(t, c), t, c) for t in TARGETS for c in prof), reverse=True)
    columns, used = {}, set()
    for conf, t, c in pairs:
        if conf >= 0.5 and t not in columns and c not in used:
            columns[t] = {"source": c, "confidence": conf}
            used.add(c)
    if "smart_194" in columns and prof[columns["smart_194"]["source"]]["med"] >= 80:
        columns["smart_194"]["transform"] = "fahrenheit_to_celsius"
    if "capacity_tb" in columns and prof[columns["capacity_tb"]["source"]]["med"] >= 1e9:
        columns["capacity_tb"]["transform"] = "bytes_to_tb"
    date_fmt = prof[columns["date"]["source"]]["date_format"] if "date" in columns else None
    missing = [t for t in TARGETS if t not in columns]
    return {"date_format": date_fmt, "columns": columns, "missing": missing}


def to_bronze(file: Path, mapping: dict, bronze: Path) -> int:
    """Rewrite a customer file as bronze Parquet using only the saved mapping."""
    cols = mapping["columns"]
    src = lambda t: ident(cols[t]["source"])

    def num(t, cast="BIGINT"):
        if t not in cols:
            return f"NULL::{cast}"
        v = TRANSFORMS.get(cols[t].get("transform"), "{v}").format(v=NUM.format(c=src(t)))
        return f"round({v})::{cast}" if cast == "BIGINT" else f"{v}::{cast}"

    smart = ", ".join(f"{num(f'smart_{a}')} AS smart_{a}_raw" for a in ATTRS)
    run_id, schema = (
        uuid.uuid4().hex[:12],
        hashlib.md5(yaml.dump(mapping).encode()).hexdigest()[:12],
    )
    bronze.mkdir(parents=True, exist_ok=True)
    duckdb.sql(f"""COPY (SELECT {src("drive_id")} AS serial_number,
        try_strptime({src("date")}, '{mapping["date_format"]}')::DATE AS date,
        {src("model")} AS model, ({num("capacity_tb", "DOUBLE")} * 1e12)::BIGINT AS capacity_bytes,
        {num("failure", "INTEGER")} AS failure, {smart},
        '{run_id}' AS _run_id, 'onboard-{schema}' AS _schema_hash
        FROM read_csv('{file}', all_varchar = true)) TO '{bronze}/data.parquet'""")
    return duckdb.sql(f"SELECT count(*) FROM '{bronze}/data.parquet'").fetchall()[0][0]


def parse_failures(file: Path, mapping: dict) -> dict[str, int]:
    """Non-empty values per mapped column that could not be parsed (they become null)."""
    checks = {
        t: f"try_strptime({ident(c['source'])}, '{mapping['date_format']}')"
        if t == "date"
        else NUM.format(c=ident(c["source"]))
        for t, c in mapping["columns"].items()
        if t not in ("drive_id", "model")
    }
    sql = ", ".join(
        f"count(nullif(trim({ident(mapping['columns'][t]['source'])}), '')) - count({e})"
        for t, e in checks.items()
    )
    row = duckdb.sql(f"SELECT {sql} FROM read_csv('{file}', all_varchar = true)").fetchall()[0]
    return {t: n for t, n in zip(checks, row) if n}


def apply(file: Path, mapping: dict, fleet: str, data: Path, model_dir: Path) -> dict:
    """File -> bronze -> clean -> features -> score for the file's last day."""
    need = {"drive_id", "date", "model"} - set(mapping["columns"])
    if need:
        raise ValueError(f"mapping is missing required columns: {sorted(need)}")
    to_bronze(file, mapping, data / "bronze")
    r, jumps = clean.run(data)
    if jumps:
        raise ValueError(f"null rate jumped: {jumps}")
    report = max((data / "reports").glob("*.json"))
    r["parse_failures"] = parse_failures(file, mapping)
    report.write_text(json.dumps(r, indent=2))
    features(data / "silver", data / "gold")
    r["scored"] = score(date.fromisoformat(r["data_end"]), fleet, data, model_dir)
    return r
