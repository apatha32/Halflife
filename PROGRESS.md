# Progress

## Steps
- [x] 1. Probe
- [x] 2. Ingest (bronze) — full run: 24 months, 22,490,291 rows, 862 failures, ~10 min, 882 MB
- [x] 3. Clean (silver) — fixture: 2,337,844 in, 350 quarantined, 241 counter resets on 137 drives
- [x] 4. Quality report — data/reports/<run_at>.json + .md; fixture: 2,337,844 in = 2,337,494 out + 350 quarantined
- [x] 5. Features and model — full run: test PR-AUC LightGBM 0.078 / logistic 0.061 / naive 0.021; P@50 11.7% vs 3.8%; R@50 18.1% vs 5.9%. Model 20261104-1138.
- [x] 6. Supabase — local stack via CLI; RLS pgTAP test passes (4 assertions); demo password login works
- [x] 7. Scoring — 2025-12-31: 34,147 Acme drives scored; re-run leaves 34,187 scores (incl. 40 seed), 179,244 history rows, 1 report
- [x] 8. Web app — verified in headless Chrome at 375px: login, demo login, pull list (25/page, CSV 500 rows), drive detail, data quality, RLS (Acme cannot open Northwind drives), no horizontal overflow
- [x] 9. Onboarding — Northwind CSV (36,204 rows) -> 712 duplicates quarantined -> 300 drives scored using only mappings/northwind.yaml; coverage 0.77 vs Acme 0.85
- [x] 10. Deploy prep and README — Docker image builds (2.2 GB, non-root) and runs clean+features on the fixture; deploy steps in docs/deploy.md
- [x] Finish: 12 Python tests + RLS pgTAP test pass, lint passes, review fixes below

## Decisions
- Iceberg access follows Backblaze's "Iceberg on B2" post: `iceberg_scan(path, version='?', allow_moved_paths=true)` with `unsafe_enable_version_guessing`; no metadata file path needed.
- Date filter prunes: table is partitioned by `date_month`; 2024-06-01 read 1 of 718 live data files (286,791 rows, 286,791 drives, 197 columns). 2024-2025 = 327 files, 222.8M rows.
- `.env` holds the public read-only key published in that post; env is loaded with `uv run --env-file ../.env` (no python-dotenv).
- Sampling: `md5_number_lower(serial_number) % 10000 < pct*100` — stable across runs/DuckDB versions and nested, so the 1% fixture is a subset of the 10% bronze and is written in the same pass.
- Schema hash = md5 of the sorted columns that are non-null in that month (Iceberg exposes one unified 197-col schema, so "which attributes are reported" is the drift signal). 5 hashes across 2024-2025.
- Partition = month file `data/bronze/year=Y/month=MM/data.parquet`; re-ingest overwrites the file (verified: 2024-06 re-run gave the same 870,357 rows).
- 1% fixture (`workers/tests/fixtures/onepct/`, 2.34M rows, 3,882 drives, 82 failures, 86 MB) is git-ignored: it is data. Unit tests use tiny inline fixtures instead.
- `DATA_DIR` env (default `<repo>/data`) lets every step run against the fixture: `DATA_DIR=workers/tests/fixtures/onepct`.
- SMART picks: 5, 9, 12, 187, 188, 194, 197, 198, 199 (see docs/decisions/0001). Counters rebased: 5, 9, 12, 187, 188, 198, 199; 194/197 are gauges.
- Silver is a full recompute (counter rebasing needs whole-drive history), written as three files that are overwritten each run: drive_days, lifecycle, quarantine.
- Quarantine reasons, first match wins: missing_key, duplicate (keep failure row / larger capacity), after_failure (rows after a drive's first failure — one fixture drive "failed" twice), bad_capacity (<=0; 346 fixture rows, none failures), bad_temperature (not 1-100 C), bad_power_on_hours (>20 years), negative_smart.
- Manufacturer from a model-prefix dict; unknown prefixes -> 'Other'.
- DuckDB 2.0: relations have no fetchone() and an unfinished execute() result blocks the connection, so code uses fetchall().
- Quality report compares to the newest previous JSON in reports/; the run writes the report first, then exits 1 if any null rate rose by more than NULL_RATE_MAX_JUMP (default 0.05 = 5 points), so the failing report is kept for inspection.
- Gold keeps rows whose H-day window passes the data end, with y = NULL: training skips them, scoring needs the latest day's features.
- Leakage test compares features computed with and without sentinel future rows (exact-equality "sentinel in features" check missed a deliberately broken window because leaks get mixed into averages/deltas). Verified it fails when the frame is changed to FOLLOWING.
- Splits: labeled days split 60/20/20 with 30-day gaps (= horizon, so no label window crosses a split). Validate/test evaluated on Monday snapshots (weekly pull cadence; also keeps memory small on 8 GB).
- Train negatives downsampled to NEG_SAMPLE_RATE=5% by md5(drive_id||date) (deterministic); both models also use class_weight='balanced' as asked.
- Naive rule ranks by smart_5 + smart_197 (flag = > 0) so top-K is defined.
- Logistic: arcsinh -> median impute -> scale; numeric features only. LightGBM gets drive model as a categorical code (codes saved in model.pkl).
- K = WEEKLY_CAPACITY (default 50 drives/week ~= 0.14% of the ~35k-drive 10% fleet). Precision@K = mean over weekly snapshots; recall@K = caught / all positives across snapshots.
- Best model picked on validation PR-AUC (not test). models/<version>/ is committed (1 MB) so scoring and deploy work without retraining.
- Full clean: 22,490,291 in = 22,485,165 out + 5,126 quarantined (3,312 bad_capacity, 1,814 after_failure); 2,458 counter resets fixed; 860 failed drives.
- RLS: one `is_member(fleet_id)` security-definer helper used by every select policy; no insert/update policies, so only the service-role key writes. `pull_list` is security invoker so RLS applies to it.
- quality_reports carries fleet_id (Acme gets pipeline reports, Northwind its onboarding reports) so it is a fleet table under RLS too.
- drive_scores also has age_days (pull list column) and coverage (step 9) so the schema stays one migration.
- Seed: fleets Acme Storage / Northwind, demo@acme.test and demo@northwind.test (password halflife-demo), 20 placeholder SEED- drives per fleet scored 2025-01-01; real scores have later dates, and pull_list shows the latest date.
- RLS test runs with `supabase test db` (make test-db) and as a separate CI job that starts the Supabase DB.
- SHAP via LightGBM `pred_contrib=True` (exact TreeSHAP, no `shap` dependency); logistic fallback uses coef x standardized value. Only risk-raising contributions become labels; missing values get "<attribute> not reported".
- Supabase writes are PostgREST upserts over httpx (one small dependency, vs supabase-py) in 1,000-row batches, keyed on the table primary keys.
- drive_history is sent for the top 1,000 ranked drives only (180 days each ~= 180k rows); all ~34k would be ~6M rows per run for pages nobody opens.
- Rebased counters are cast back to BIGINT in clean (sum() widened them to HUGEINT -> floats).
- Risk is a ranking score, not a calibrated probability (negatives downsampled + class weights push top risks to ~1.0). The UI shows rank and relative risk.
- coverage = share of the 9 SMART attributes the drive reports that day (Toshiba/HGST lack 187/188 -> 0.78).
- Web: Next 16 `proxy.ts` (renamed middleware) refreshes the Supabase session; every page uses the anon key + user cookies so RLS applies. No service-role key in web/.
- Demo login = password sign-in for the seeded demo users; buttons only show when DEMO_PASSWORD is set (server-only env). Magic link uses `shouldCreateUser: false`, so only invited users can sign in.
- Chart: Recharts. Sensor counters and temperature are two stacked panels sharing the x axis (no dual axis); risk is overlaid as a dashed marker at the score date because risk exists only on scoring dates. Validated default palette (slots 1-4); its low-contrast WARN is relieved by legend, tooltips and a "history as a table" view.
- Mobile: Model and Age columns hide below 640px so Risk and Top driver fit at 375px.
- Onboarding confidence = 0.6 x best difflib ratio vs target aliases + 0.4 x a value-range check (temps with median 80-130 => Fahrenheit transform; failure must be 0/1; dates pick the format with the best parse rate). Greedy one-to-one assignment, threshold 0.5. Text columns profile with NaN ranges so numeric checks are simply false.
- `--apply` reads only the saved YAML; data goes to data/fleets/<slug>/{bronze,silver,gold,reports} and reuses clean.run -> features -> score. Required columns (drive_id, date, model) are checked at this boundary.
- Clean + report gating moved into clean.run()/report.save() so the CLI and onboarding share them.
- Alias lists include the names used by make_northwind.py, so Northwind scores 1.0 on every column; real customer files would rely more on the value checks. Logged as a limitation.
- Docker: build context is the repo root so the committed model ships in the image; package installed editable so ROOT resolves to /app; base image pinned to ghcr.io/astral-sh/uv:0.13.4-python3.12-trixie-slim (no bookworm tag for 0.13.4); libgomp1 for LightGBM.
- Railway mounts volumes as root, so the deploy sets RAILWAY_RUN_UID=0 rather than dropping the non-root user from the image.
- railway.json runs ingest -> clean -> features -> score once (restartPolicyType NEVER); train is not in the job — the committed model is used.

## Review (finish)
Fixed:
- HIGH, idempotency/data loss: `ingest --start/--end` inside a month overwrote that month's partition with only the requested days (a nightly 1-day ingest would have wiped the month). Ingest now always processes whole months; test added.
- MEDIUM, SQL injection: customer CSV column names were interpolated inside "..." unescaped. Now quoted via `ident()`; test with a quote in a header.
- LOW: latest-model lookup used max(iterdir()) (stray files could win); now the newest `*/model.pkl`. score() trimmed from 43 lines (shared REST helper, history() split out).
Checked, no change needed:
- Silent row drops: bronze -> silver adds up (rows in = out + quarantined, every quarantined row has a reason); features join to lifecycle is lossless (22,485,165 = 22,485,165); training only drops y = NULL rows by design.
- Time leakage: all windows are PRECEDING..CURRENT ROW (sabotage-tested), splits have 30-day gaps = horizon, downsampling and imputer fitting use train only, model chosen on validation.
- Secrets: .env, web/.env.local, data/ and the fixture are untracked; only the service role writes; web uses the anon key + user session.
Known limitations (not fixed):
- Onboarding: values that fail to parse become NULL without a per-value count; the null-rate section of the quality report is the only signal.
- Re-scoring a date with fewer drives leaves earlier rows for drives no longer present (upsert never deletes).
- Onboarding aliases include Northwind's own column names, so its 1.0 confidences overstate how well name matching generalizes.
- Model risk is not calibrated; the image is 2.2 GB; the seed demo users have public passwords.

## Phase 2: design (2026-11-04)
- [x] Web app restyled: black/white with neon green (#39ff14), JetBrains Mono, scanline nav, staggered row entrances, glow on the top 3 risks, line-draw chart animation; all motion off under prefers-reduced-motion. Chart series told apart by green/white/gray plus dash patterns (legend + table view kept). No emojis or em dashes. Re-verified at 375px.
- [x] GitHub Pages site in site/ (single static page, no build): animated stats, system design diagram in white + neon pink with flowing edges, pipeline, data-quality counts, model results with animated bars, cost curve drawn from models/<version>/cost_curve.json values. Deployed by .github/workflows/pages.yml.
- "monodragon" read as monochrome + mono typeface.
- [x] Smooth transitions: React `<ViewTransition>` crossfades the page area on every route change (blur + slide, 0.25s out / 0.5s in); the drive ID morphs from its pull-list row into the drive page heading; one shared ease-out curve for hovers, reveals and chart line draws. Reduced motion disables all of it.
- [x] Fonts: SF Pro (text) and SF Mono (labels, numbers, IDs) via system font stacks; no web font download. Non-Apple systems fall back to system-ui / Menlo / Consolas.
- [x] Shades: green scale neon-50..900 and grey scale; gradients on panels, buttons, table heads, bars and the hero; pull-list rank/risk shaded by tier (top 3 glow, 4-10, 11-50, rest). Site diagram uses pink shades (group lines, labels, edges).
- Verified in Chrome: route crossfade on every navigation, drive ID morph pull list -> drive page, no animations under reduced motion, no errors.
- [x] Background: pure black with a fixed layer from the left edge: green radial + linear shade (breathes over 9s) and a 135-degree line pattern masked to fade out by ~60% width (drifts over 40s). Same in app and site; static under reduced motion. Fixed position, so it holds still across scroll and route transitions.

## Phase 3: nightly updates and alerts (2026-11-08)
- [x] `halflife nightly`: resume from the newest bronze month (re-ingested, it may have grown) or INGEST_START, ingest through the newest published day, clean, features, score that day, alerts. Railway cron 06:00 UTC.
- [x] Alerts: `alerts` table + `make_alerts(fid, day, k, jump=100)` SQL function. Entered top K, or rose >= 100 ranks into the top 10K, vs the previous non-seed scoring date. Returns only newly inserted rows (re-runs alert nothing). Execute revoked from anon/authenticated. pgTAP test covers both kinds, idempotency, RLS and the revoke.
- [x] Delivery: /alerts page in the app; Slack incoming webhook when SLACK_WEBHOOK_URL is set (no new dependency, httpx).
- [x] Stale scores: each run stamps scored_at and deletes that fleet/day's rows it did not write.
- Decisions: logic lives in SQL so the worker, re-runs and tests share one definition. Onboarding does not raise alerts (one snapshot, no previous day). No retraining in the nightly job.
- Verified locally: nightly ingested 2025-12..2026-09 (10 months), scored 37,291 drives for 2026-09-30, 359 alerts (44 entered top K, 315 rank jumps) in 6 min with 2.5 GB peak RAM. Re-run: only 2026-09 re-ingested, 0 new alerts, same counts. Planted stale score was deleted on re-score. Alerts page checked at 1280 and 375 px; Northwind sees none.
- CLIs: Homebrew failed (outdated Command Line Tools; vercel moved to a cask) and global npm needs root, so Railway 5.71.0 and Vercel 65.12.1 are installed with `npm i -g --prefix ~/.local`.

## Cleanups (2026-11-08)
- [x] Worker image 2.17 GB -> 1.21 GB: build as the app user with COPY --chown (the old `chown -R` layer duplicated every file), UV_NO_CACHE, and matplotlib moved to dev deps (only train draws the cost curve; imported inside plot()).
- [x] CI actions on current majors: checkout v7, setup-node v7, setup-uv v10, setup-cli v3 (pinned CLI 2.121.0), upload-pages-artifact v5, deploy-pages v5.

## Phase 4: model upgrades (2026-11-08)
- [x] Labels for 7/30/90 days (y_7, y_30, y_90; NULL when the window passes the data end). HORIZON_DAYS env removed.
- [x] Calibration: Platt scaling on validation Monday snapshots (rank-preserving, so the pull list order is unchanged). Risk is now a probability. Test (2026-03-01..2026-08-31): 30d Brier 0.000995, expected 900 vs observed 1,015 failure-days (about 11% under).
- [x] Time to failure: separate calibrated LightGBM heads for 7 and 90 days; scores kept monotone (7 <= 30 <= 90). Stored as drive_scores.risk_7d / risk_90d; drive page shows all three. This is a discrete-time stand-in for a survival model, not a Cox/AFT fit.
- [x] Drift: training saves per-feature decile reference; nightly computes PSI of the newest day and a backtest on the latest fully labeled Monday, stored as model_health in the quality report and shown on the data-quality page.
- Retrained on 2024-01..2026-09 (model 20261108-1541; old 20261104-1138 removed, its artifact format is incompatible). Test: LightGBM PR-AUC 0.105 vs naive 0.052, P@50 15.9% vs 7.7%, R@50 21.2% vs 10.3%.
- Real drift found: power-on hours / age PSI 0.37 (fleet older than training data). Retraining on newer data is the obvious follow-up.
- Known: re-scoring a day with a new model creates alerts for drives that newly enter the top K under that model (148 on 2026-09-30); alerts are never deleted.

## Phase 5: customer upload (2026-11-08)
- [x] Roles: memberships.role admin/viewer; seeded demo users are viewers (public password, so no uploads). `is_admin()` helper.
- [x] Storage: private `uploads` bucket (text/csv, 20 MB); admins write only under their fleet's folder, members read.
- [x] `uploads` table with status flow uploaded -> needs_review -> approved -> processing -> scored/failed. Column grants: users may insert (fleet_id, path, filename) and update (mapping, status) only; RLS limits updates to admins and needs_review -> approved.
- [x] Web: /upload (browser uploads straight to Storage with the user session, avoiding Vercel's 4.5 MB function body limit) and /upload/[id] review form (dropdown per field prefilled from the proposal with confidence, temperature unit, capacity unit, date format; required fields enforced).
- [x] Worker: `halflife uploads` proposes mappings for new files and runs approved ones through onboard.apply; failures are recorded on the upload (the one deliberate broad except). Deployed as a second Railway cron (every 10 minutes, no volume).
- [x] Onboarding gaps: unparseable values counted per column (parse_failures in the result and quality report, shown in the app); smartctl-style names and capacity in bytes now matched (tested). Those aliases were added before the test, so it proves the common format, not arbitrary files.
- Verified in Chrome at 375 px: viewer sees uploads off; admin uploads Northwind CSV, mapping proposed correctly for every field (Fahrenheit, MM/DD/YYYY), approved, 300 drives scored, 712 duplicates quarantined. pgTAP: 7 upload permission checks.
- Known: a new upload replaces that fleet's data (no upload history yet).
- Docs: README, docs/deploy.md (uploads service, roles), evaluation.md and the project page updated to the 2024-01..2026-09 data and model 20261108-1541.

## Next session
- Only deploy is left: user runs `supabase login`, `railway login`, `vercel login` (Railway Hobby $5 plan confirmed; CLIs installed in ~/.local). Then follow docs/deploy.md, including the second Railway service for uploads. Optional: Slack webhook URL.
