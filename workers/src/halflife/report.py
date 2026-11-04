from datetime import UTC, datetime


def build(con, prev: dict | None) -> dict:
    """Summarize a clean run from its tagged/drive_days/lifecycle/quarantine tables."""

    def one(sql):
        return con.execute(sql).fetchall()[0][0]

    def pairs(sql):
        return dict(con.execute(sql).fetchall())

    cols = [c for c in con.table("drive_days").columns if c.startswith("smart_")]
    rates = con.execute(
        "SELECT " + ", ".join(f"1 - count({c}) / count(*)" for c in cols) + " FROM drive_days"
    ).fetchall()[0]
    null_rates = {c: round(r, 4) for c, r in zip(cols, rates)}
    old = (prev or {}).get("null_rates", {})
    return {
        "run_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "data_start": str(one("SELECT min(date) FROM drive_days")),
        "data_end": str(one("SELECT max(date) FROM drive_days")),
        "rows_in": one("SELECT count(*) FROM tagged"),
        "rows_out": one("SELECT count(*) FROM drive_days"),
        "quarantined": pairs("SELECT reason, count(*) FROM quarantine GROUP BY 1 ORDER BY 2 DESC"),
        "quarantined_failures": one("SELECT count(*) FROM quarantine WHERE failure = 1"),
        "resets_fixed": one("SELECT count(*) FROM drive_days WHERE reset_event"),
        "rows_rebased": one("SELECT count(*) FROM drive_days WHERE rebased"),
        "drives": pairs("SELECT end_reason, count(*) FROM lifecycle GROUP BY 1 ORDER BY 2 DESC"),
        "schema_hashes": pairs(
            "SELECT _schema_hash, count(*) FROM tagged GROUP BY 1 ORDER BY min(date)"
        ),
        "null_rates": null_rates,
        "null_rate_change": {c: round(r - old[c], 4) for c, r in null_rates.items() if c in old},
    }


def render(r: dict) -> str:
    """Render a quality report dict as Markdown."""
    rows = lambda d: "\n".join(f"| {k} | {v:,} |" for k, v in d.items())
    change = r["null_rate_change"]
    nulls = "\n".join(
        f"| {c} | {v:.2%} | {change[c]:+.2%} |" if c in change else f"| {c} | {v:.2%} | — |"
        for c, v in r["null_rates"].items()
    )
    return f"""# Data quality report — {r["run_at"]}

Data {r["data_start"]} to {r["data_end"]}. Rows in {r["rows_in"]:,}, rows out {r["rows_out"]:,},
quarantined {sum(r["quarantined"].values()):,} ({r["quarantined_failures"]} failure rows).
Counter resets fixed: {r["resets_fixed"]:,} ({r["rows_rebased"]:,} rows rebased).

| Quarantine reason | Rows |
|---|---|
{rows(r["quarantined"])}

| Drive end reason | Drives |
|---|---|
{rows(r["drives"])}

| Schema hash | Rows |
|---|---|
{rows(r["schema_hashes"])}

| Column | Null rate | Change vs previous run |
|---|---|---|
{nulls}
"""
