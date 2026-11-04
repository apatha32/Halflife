"""Show the Drive Stats schema, one day's row/drive counts, and data files read.

Run from workers/: uv run --env-file ../.env python ../scripts/probe_day.py 2024-06-01
"""

import sys

from halflife.ingest import connect

day = sys.argv[1] if len(sys.argv) > 1 else "2024-06-01"
con, src = connect()
print(con.sql(f"DESCRIBE SELECT * FROM {src}"))
q = f"SELECT count(*) AS rows, count(DISTINCT serial_number) AS drives FROM {src} WHERE date = DATE '{day}'"
print(con.sql(q))
plan = con.execute(f"EXPLAIN ANALYZE {q}").fetchall()[0][1]
print("\n".join(line for line in plan.splitlines() if "File" in line))
