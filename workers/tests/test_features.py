import duckdb

from halflife.clean import ATTRS
from halflife.features import FEATURES, features

SENTINEL = 999_999


def make_silver(path, rows):
    path.mkdir(parents=True)
    smart = ", ".join(f"v AS smart_{a}" for a in ATTRS)
    duckdb.sql(f"""COPY (SELECT s AS drive_id, d::DATE AS date, 'M' AS model, 'Seagate' AS manufacturer,
        4.0 AS capacity_tb, f AS failure, {smart}
        FROM (VALUES {rows}) t(s, d, v, f)) TO '{path}/drive_days.parquet'""")
    duckdb.sql(f"""COPY (SELECT drive_id, min(date) FILTER (failure = 1) AS failure_date
        FROM '{path}/drive_days.parquet' GROUP BY 1) TO '{path}/lifecycle.parquet'""")


def test_no_feature_reads_future_rows(tmp_path):
    past = ", ".join(f"('A', DATE '2024-01-01' + {i}, {i}, 0)" for i in range(40))
    future = ", ".join(f"('A', DATE '2024-02-10' + {i}, {SENTINEL}, 0)" for i in range(40))
    for name, rows in [("past", past), ("all", f"{past}, {future}")]:
        make_silver(tmp_path / name / "silver", rows)
        features(tmp_path / name / "silver", tmp_path / name / "gold")
    cols = ", ".join(["date", *FEATURES])
    a, b = (
        duckdb.sql(f"SELECT {cols} FROM '{tmp_path}/{n}/gold/features.parquet' ORDER BY date")
        .limit(40)
        .fetchall()
        for n in ("past", "all")
    )
    assert a == b and all(SENTINEL not in row for row in b)
    assert duckdb.sql(f"""SELECT smart_5_d7, smart_5_d30 FROM '{tmp_path}/all/gold/features.parquet'
        WHERE date = DATE '2024-01-31'""").fetchall() == [(7, 30)]


def test_label_horizon_and_end_of_data(tmp_path):
    rows = ", ".join(f"('A', DATE '2024-01-01' + {i}, 0, {int(i == 50)})" for i in range(51))
    rows += ", " + ", ".join(f"('B', DATE '2024-01-01' + {i}, 0, 0)" for i in range(100))
    make_silver(tmp_path / "silver", rows)
    features(tmp_path / "silver", tmp_path / "gold")
    y = dict(
        duckdb.sql(f"""SELECT drive_id || date, y_30 FROM '{tmp_path}/gold/features.parquet'
        WHERE date IN ('2024-01-21', '2024-01-22', '2024-03-10', '2024-03-11')""").fetchall()
    )
    assert y["A2024-01-21"] is False and y["A2024-01-22"] is True
    assert y["B2024-03-10"] is False and y["B2024-03-11"] is None
    y7 = dict(
        duckdb.sql(f"""SELECT drive_id || date, y_7 FROM '{tmp_path}/gold/features.parquet'
        WHERE drive_id = 'A' AND date IN ('2024-02-13', '2024-02-14')""").fetchall()
    )
    assert y7 == {"A2024-02-13": False, "A2024-02-14": True}
