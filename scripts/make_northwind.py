"""Export a messy "Northwind" CSV from silver to exercise `halflife onboard`.

Run from workers/: uv run python ../scripts/make_northwind.py
Renamed columns, Fahrenheit temps, MM/DD/YYYY dates, numbers as strings with
commas, SMART 187/188 missing, ~2% duplicate rows. 300 drives, last 120 days.
"""

import duckdb

from halflife import DATA

out = DATA / "northwind"
out.mkdir(parents=True, exist_ok=True)
num = lambda c: f"format('{{:,}}', {c}::BIGINT)"  # noqa: E731
duckdb.sql(f"""
CREATE TABLE nw AS
SELECT 'NW-' || drive_id AS "Serial No", strftime(date, '%m/%d/%Y') AS "Reading Date",
  model AS "Drive Model", round(capacity_tb, 1)::VARCHAR AS "Size (TB)", failure AS "Failed?",
  {num("smart_5")} AS "Realloc Sector Ct", {num("smart_9")} AS "Power On Hrs",
  {num("smart_12")} AS "Power Cycle Count", round(smart_194 * 9 / 5 + 32)::VARCHAR AS "Temp",
  {num("smart_197")} AS "Pending Sectors", {num("smart_198")} AS "Offline Uncorrectable",
  {num("smart_199")} AS "CRC Error Count"
FROM '{DATA}/silver/drive_days.parquet'
WHERE date > DATE '2025-12-31' - 120
  AND drive_id IN (SELECT DISTINCT drive_id FROM '{DATA}/silver/drive_days.parquet'
                   WHERE date = '2025-12-31' ORDER BY md5(drive_id) LIMIT 300)
""")
duckdb.sql(f"""COPY (SELECT * FROM nw UNION ALL SELECT * FROM nw USING SAMPLE 2% (bernoulli, 7)
    ORDER BY "Serial No", "Reading Date") TO '{out}/northwind.csv'""")
print(duckdb.sql(f"SELECT count(*) FROM '{out}/northwind.csv'").fetchall(), out / "northwind.csv")
