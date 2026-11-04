import duckdb

from halflife.onboard import profile, propose, to_bronze

CSV = """Serial No,Reading Date,Drive Model,Size (TB),Failed?,Realloc Sector Ct,Temp,Power On Hrs
{rows}"""


def test_propose_detects_columns_fahrenheit_and_dates_then_converts(tmp_path):
    rows = "\n".join(
        f'NW-{i % 20},{1 + i % 12:02d}/{1 + i % 28:02d}/2025,ST4000DM000,4.0,0,"1,{i:03d}",{95 + i % 10},"20,000"'
        for i in range(200)
    )
    f = tmp_path / "nw.csv"
    f.write_text(CSV.format(rows=rows))
    m = propose(profile(f))
    assert m["date_format"] == "%m/%d/%Y"
    assert {t: c["source"] for t, c in m["columns"].items()} == {
        "drive_id": "Serial No",
        "date": "Reading Date",
        "model": "Drive Model",
        "capacity_tb": "Size (TB)",
        "failure": "Failed?",
        "smart_5": "Realloc Sector Ct",
        "smart_194": "Temp",
        "smart_9": "Power On Hrs",
    }
    assert m["columns"]["smart_194"]["transform"] == "fahrenheit_to_celsius"
    assert "smart_187" in m["missing"]
    to_bronze(f, m, tmp_path / "bronze")
    b = duckdb.sql(
        f"SELECT min(smart_194_raw), max(smart_5_raw), max(smart_9_raw), count(smart_187_raw), "
        f"min(date) FROM '{tmp_path}/bronze/data.parquet'"
    ).fetchall()[0]
    assert b[:4] == (35, 1199, 20000, 0) and str(b[4]) == "2025-01-01"


def test_column_names_with_quotes_are_safe(tmp_path):
    f = tmp_path / "q.csv"
    f.write_text('"Serial ""No""",Date,Model\nA,2025-01-01,M\nB,2025-01-01,M\n')
    assert profile(f)['Serial "No"']["distinct"] == 2
