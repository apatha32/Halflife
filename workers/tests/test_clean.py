import duckdb

from halflife.clean import clean

ROWS = """('A', DATE '2024-01-01', 10, 40, 0, 4e12), ('A', DATE '2024-01-02', 12, 40, 0, 4e12),
  ('A', DATE '2024-01-03', 0, 40, 0, 4e12), ('A', DATE '2024-01-04', 3, 40, 1, 4e12),
  ('A', DATE '2024-01-05', 3, 40, 0, 4e12),
  ('B', DATE '2024-01-01', 0, 30, 0, 4e12), ('B', DATE '2024-01-01', 0, 30, 0, 4e12),
  ('B', DATE '2024-01-04', 0, 30, 0, 4e12), ('C', DATE '2024-01-04', 0, 30, 0, -1),
  ('C', DATE '2024-01-02', 0, 250, 0, 4e12), ('C', DATE '2024-01-03', 0, 35, 0, 4e12),
  (NULL, DATE '2024-01-02', 0, 35, 0, 4e12)"""


def make_bronze(path):
    path.mkdir(parents=True)
    smart = ", ".join(f"NULL::BIGINT AS smart_{a}_raw" for a in [9, 12, 187, 188, 197, 198, 199])
    duckdb.sql(f"""COPY (SELECT s AS serial_number, d AS date, 'ST4000DM000' AS model,
        cap::BIGINT AS capacity_bytes, f AS failure, r5::BIGINT AS smart_5_raw,
        t::BIGINT AS smart_194_raw, {smart}, 'h1' AS _schema_hash
        FROM (VALUES {ROWS}) v(s, d, r5, t, f, cap)) TO '{path}/data.parquet'""")


def test_clean_rebases_quarantines_and_builds_lifecycle(tmp_path):
    make_bronze(tmp_path / "bronze")
    con = clean(tmp_path / "bronze", tmp_path / "silver")
    a = con.sql(
        "SELECT smart_5, reset_event, rebased FROM drive_days WHERE drive_id='A' ORDER BY date"
    )
    assert a.fetchall() == [
        (10, False, False),
        (12, False, False),
        (12, True, True),
        (15, False, True),
    ]
    q = con.sql("SELECT reason, count(*) FROM quarantine GROUP BY 1 ORDER BY 1").fetchall()
    assert q == [
        ("after_failure", 1),
        ("bad_capacity", 1),
        ("bad_temperature", 1),
        ("duplicate", 1),
        ("missing_key", 1),
    ]
    assert con.execute("SELECT count(*) FROM drive_days").fetchall()[0][0] == 12 - 5
    life = con.sql("SELECT drive_id, end_reason FROM lifecycle ORDER BY 1").fetchall()
    assert life == [("A", "failed"), ("B", "still_active"), ("C", "retired_or_missing")]
    assert con.execute("SELECT manufacturer FROM drive_days LIMIT 1").fetchall()[0][0] == "Seagate"


def test_report_rows_add_up_and_null_jump_is_measured(tmp_path):
    from halflife import report

    make_bronze(tmp_path / "bronze")
    con = clean(tmp_path / "bronze", tmp_path / "silver")
    r = report.build(con, {"null_rates": {"smart_5": 0.0, "smart_9": 0.5}})
    assert r["rows_in"] == r["rows_out"] + sum(r["quarantined"].values()) == 12
    assert r["resets_fixed"] == 1 and r["null_rate_change"] == {"smart_5": 0.0, "smart_9": 0.5}
    assert "| duplicate | 1 |" in report.render(r)
