from datetime import date

import duckdb

from halflife import ingest as ing


def test_ingest_month_samples_whole_drives_and_overwrites(tmp_path, monkeypatch):
    monkeypatch.setattr(ing, "DATA", tmp_path / "data")
    monkeypatch.setattr(ing, "FIXTURE", tmp_path / "fx")
    con = duckdb.connect()
    con.execute(
        "CREATE TABLE src AS SELECT DATE '2024-01-01' + d::INT AS date, 'S' || s AS serial_number, "
        "NULL::BIGINT AS smart_1_raw, s AS smart_5_raw FROM range(40) t(d), range(500) u(s)"
    )
    for _ in range(2):
        n = ing.ingest_month(con, "src", date(2024, 1, 1), date(2024, 1, 31), 10, "r1")
    out = duckdb.sql(f"SELECT * FROM '{tmp_path}/data/bronze/year=2024/month=01/data.parquet'")
    days = duckdb.sql("SELECT count(DISTINCT date) d FROM out GROUP BY serial_number").fetchall()
    assert n == len(out) and 0 < n < 500 * 31
    assert set(days) == {(31,)}
    hashes = duckdb.sql("SELECT DISTINCT _schema_hash, _run_id FROM out").fetchall()
    assert len(hashes) == 1 and hashes[0][1] == "r1"
    fx = duckdb.sql(f"SELECT DISTINCT serial_number FROM '{tmp_path}/fx/bronze/**/*.parquet'")
    sub = duckdb.sql("SELECT DISTINCT serial_number FROM out")
    assert 0 < len(fx) < len(sub) and not fx.except_(sub).fetchall()


def test_partial_range_reingests_whole_month(tmp_path, monkeypatch):
    monkeypatch.setattr(ing, "DATA", tmp_path / "data")
    monkeypatch.setattr(ing, "FIXTURE", tmp_path / "fx")
    con = duckdb.connect()
    con.execute(
        "CREATE TABLE src AS SELECT DATE '2024-01-01' + d::INT AS date, 'S' || s AS serial_number "
        "FROM range(40) t(d), range(50) u(s)"
    )
    monkeypatch.setattr(ing, "connect", lambda: (con, "src"))
    ing.ingest(date(2024, 1, 15), date(2024, 1, 15), 100)
    out = f"{tmp_path}/data/bronze/year=2024/month=01/data.parquet"
    assert duckdb.sql(f"SELECT count(DISTINCT date) FROM '{out}'").fetchall() == [(31,)]
