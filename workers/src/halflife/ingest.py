import os

import duckdb


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
