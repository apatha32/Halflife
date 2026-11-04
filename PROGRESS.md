# Progress

## Steps
- [x] 1. Probe
- [ ] 2. Ingest (bronze)
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
