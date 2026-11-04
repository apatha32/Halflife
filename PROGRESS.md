# Progress

## Steps
- [x] 1. Probe
- [x] 2. Ingest (bronze) — full run: 24 months, 22,490,291 rows, 862 failures, ~10 min, 882 MB
- [ ] 3. Clean (silver)
- [ ] 4. Quality report
- [ ] 5. Features and model
- [ ] 6. Supabase
- [ ] 7. Scoring
- [ ] 8. Web app
- [ ] 9. Onboarding
- [ ] 10. Deploy prep and README
- [ ] Finish: full tests, lint, staff-engineer review

## Decisions
- Iceberg access follows Backblaze's "Iceberg on B2" post: `iceberg_scan(path, version='?', allow_moved_paths=true)` with `unsafe_enable_version_guessing`; no metadata file path needed.
- Date filter prunes: table is partitioned by `date_month`; 2024-06-01 read 1 of 718 live data files (286,791 rows, 286,791 drives, 197 columns). 2024-2025 = 327 files, 222.8M rows.
- `.env` holds the public read-only key published in that post; env is loaded with `uv run --env-file ../.env` (no python-dotenv).
- Sampling: `md5_number_lower(serial_number) % 10000 < pct*100` — stable across runs/DuckDB versions and nested, so the 1% fixture is a subset of the 10% bronze and is written in the same pass.
- Schema hash = md5 of the sorted columns that are non-null in that month (Iceberg exposes one unified 197-col schema, so "which attributes are reported" is the drift signal). 5 hashes across 2024-2025.
- Partition = month file `data/bronze/year=Y/month=MM/data.parquet`; re-ingest overwrites the file (verified: 2024-06 re-run gave the same 870,357 rows).
- 1% fixture (`workers/tests/fixtures/onepct/`, 2.34M rows, 3,882 drives, 82 failures, 86 MB) is git-ignored: it is data. Unit tests use tiny inline fixtures instead.
- `DATA_DIR` env (default `<repo>/data`) lets every step run against the fixture: `DATA_DIR=workers/tests/fixtures/onepct`.
