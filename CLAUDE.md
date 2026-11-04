# Halflife

Drive-failure prediction for a storage operator: "replace drives before
they die without pulling healthy ones." Data: Backblaze Drive Stats
(daily SMART snapshots). Cite Backblaze in README and UI.

## Stack
workers/ Python 3.12, uv, DuckDB, Polars, LightGBM, Typer CLI (Railway)
web/     Next.js App Router, TypeScript, Tailwind (Vercel)
supabase/ migrations + RLS (Supabase)
Data layers: bronze -> silver -> gold as Parquet in data/ (or S3 via env).
Only curated outputs go to Supabase.

## Code size rules (strict)
- Write the least code that meets the ask. If it can be 10 lines, it
  is 10 lines.
- Prefer one DuckDB SQL query over a Python loop or DataFrame chain.
- No new abstraction (class, base class, factory, registry, wrapper,
  config object) unless the ask names it or it is used 3+ times.
- No speculative options, flags, plugins or "future-proof" hooks.
- No new dependency without saying why in the plan.
- Functions under ~30 lines. Files under ~200 lines. Split only when
  over.
- No comments that restate the code. One-line docstrings on public
  functions only.
- No defensive checks for cases that cannot happen. Validate at the
  boundary (ingest, upload, API) only.
- Tests: the few cases that matter (happy path + named edge cases), not
  one test per line.
- In the plan, estimate lines added. If the estimate is over 150 for one
  ask, propose a smaller design first.

## Data rules
- Steps are idempotent: re-running a date replaces its partition.
- No silent drops: every removed row is counted with a reason.
- Time-based splits only; no feature for date d reads data after d.
- Secrets only in env vars; .env.example lists them all.

## Done means
Tests pass, `make lint` passes, and the diff is something you would
want to review.
