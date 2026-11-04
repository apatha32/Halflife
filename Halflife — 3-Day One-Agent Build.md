# Halflife — 3-Day One-Agent Build

Nov 4, 2026 · @Ambarish

A v1 in 3 days with one Claude Code agent: 13 small asks run in order, each short enough to review fully, with rules that keep code lean.

## How to run it

One agent builds; you run and review. Start a fresh Claude Code session for each ask so context and token use stay small.

1. Paste the ask in plan mode (Shift+Tab twice). Reject any plan that adds files, classes or dependencies the ask did not request.
2. Approve. The agent builds against the 1% fixture so every run takes seconds.
3. Read the full diff. If it feels long, run the Trim prompt before committing.
4. While the agent starts the next ask, run the full-size job yourself in a separate terminal tab.
5. Commit after every ask that passes its check.

Day targets: end of Day 1 is clean data plus a quality report; end of Day 2 is model metrics plus scores in Supabase; end of Day 3 is a deployed app and README. Anything not done moves to the README's "Next" list, not to a fourth day of scope creep.

## CLAUDE.md

Commit this at the repo root before the first ask. The code-size rules here apply to every ask, so the prompts below do not repeat them.

```markdown
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
```

## Day 1 — Clean data

Goal: silver Parquet for 2 sampled years and a quality report you would show a customer. If Iceberg access is not working within an hour, switch to the CSV path in 1B.

**1A — Scaffold** (check: `make test` passes)

```text
Read CLAUDE.md. Scaffold the repo: workers/ (uv, package `halflife`,
Typer CLI with stub commands ingest, clean, features, train, score,
onboard), web/ (Next.js placeholder page), supabase/ (CLI init),
Makefile (setup, lint, test), .env.example, .gitignore (data/, .env),
and a GitHub Actions workflow running lint + test. No pipeline logic.
```

**1B — Ingest** (check: one month lands in data/bronze; re-running changes nothing)

```text
Read CLAUDE.md. Implement `halflife ingest --start --end --sample-pct`.
Read Backblaze Drive Stats with DuckDB: the Iceberg table on B2 (connection
values from env vars), or, with --csv-dir, the quarterly CSV files.
Sample by hash of serial_number so sampled drives keep full history.
Write bronze Parquet partitioned by year/month, adding _run_id and a
schema hash. Re-ingesting a month overwrites it. First connect and show
me the schema and row count for one day before writing the rest.
Also write a 1% fixture to tests/fixtures/.
```

**1C — Canonical schema** (check: all bronze schemas map to one silver schema)

```text
Read CLAUDE.md. Profile bronze with DuckDB and show me null rates for
SMART columns by manufacturer. Then implement the first half of
`halflife clean`: map every schema hash to one canonical schema (drive_id,
date, model, manufacturer from a small mapping dict, capacity, failure,
and the SMART attributes you pick from the profile; justify the pick in
one paragraph in docs/decisions/0001-smart-attributes.md). Columns
missing in old schemas become null.
```

**1D — Resets, lifecycle, quarantine** (check: tests cover each edge case)

```text
Read CLAUDE.md. Finish `halflife clean`:
- Rebase counters that decrease within a drive; flag affected rows.
- Lifecycle table per drive: first_seen, last_seen, failed, end_reason
  in {failed, retired_or_missing, still_active}.
- Quarantine duplicates and impossible values to a separate Parquet with
  a reason column.
Prefer DuckDB window functions. Tests with tiny hand-written fixtures.
```

**1E — Quality report** (check: report counts add up: rows in = rows out + quarantined)

```text
Read CLAUDE.md. Make `halflife clean` write a quality report per run as
JSON and Markdown: rows in/out, quarantined by reason, counter resets
fixed, schema hashes seen, null-rate change vs the previous run. Fail the
run if any null rate jumps more than a threshold from env. Keep it to one
function that builds a dict and one that renders it.
```

## Day 2 — Model and backend

Goal: test-period metrics that beat the naive rule, and real scores in Supabase.

**2A — Labels, features, leakage test** (check: the leakage test fails if you break it on purpose)

```text
Read CLAUDE.md. Implement `halflife features` (silver -> gold) as DuckDB
SQL. Label y = drive fails within H days (env, default 30); drop rows
whose window passes the data end. Features per drive using only data up
to that date: age, model, capacity, each SMART value plus 7- and 30-day
deltas, temperature 7-day mean. Add a leakage test: put sentinel values in
future rows of a fixture and assert no feature contains them.
```

**2B — Models and cost curve** (check: a results table for 3 models on the test split)

```text
Read CLAUDE.md. Implement `halflife train`. Time split: train, validate,
test by date with a 30-day gap between each. Models: naive rule (any
reallocated or pending sectors > 0), logistic regression, LightGBM with
class weights. Downsample negatives in train only. Report PR-AUC and
precision/recall at K (K = weekly replacement capacity from env). Save a
cost curve (failures avoided vs healthy drives pulled for K from 0.01% to
1%) as JSON + PNG. Save the best model, metrics and feature list to
models/<version>/. Print a results table. One file for training, one for
evaluation.
```

**2C — Supabase schema, RLS, seed** (check: a user in fleet A reads zero rows from fleet B)

```text
Read CLAUDE.md. Write one Supabase migration: fleets, memberships
(user_id, fleet_id), drives, drive_scores (fleet_id, drive_id,
score_date, risk, rank, top_drivers jsonb, model_version), drive_history
(last 180 days of chosen SMART values), quality_reports (jsonb). RLS on
every fleet table via memberships. One SQL function pull_list(fleet_id,
k). A seed script with two fleets, two demo users and fake scores so the
web app can be built before real scores exist. Add one RLS isolation test.
```

**2D — Scoring** (check: re-running a date gives the same row count, no duplicates)

```text
Read CLAUDE.md. Implement `halflife score --date`. Score every drive active
on that date with the saved model, add rank and top 3 SHAP drivers as
plain labels, and upsert to drive_scores keyed by (fleet_id, drive_id,
score_date) in batches with the service-role key. Also upsert
drive_history and that day's quality report. Assign drives to the demo
fleet "Acme Storage".
```

## Day 3 — Product and story

Goal: a deployed app, a working onboarding path for a messy customer, and a README with real numbers.

**3A — Pull list and drive detail** (check: works on seed data at 375px wide)

```text
Read CLAUDE.md. In web/, add Supabase Auth (magic link) and two pages,
server components only, using the user's session so RLS applies:
- /pull-list: pull_list() as a table (drive, model, age, risk, top
  driver), paginated, with CSV export.
- /drives/[id]: line chart of drive_history with risk overlaid, and the
  top 3 drivers as sentences.
Use Tailwind and one chart library. No component library. No service
role key in web/.
```

**3B — Data quality page** (check: shows the latest real report)

```text
Read CLAUDE.md. Add /data-quality listing quality_reports newest first:
rows in/out, quarantine reasons, resets fixed, schema changes. Add a nav
bar and a footer crediting Backblaze Drive Stats. Reuse the table
component from /pull-list.
```

**3C — Onboarding a messy customer** (check: Northwind goes from file to scores using only a saved mapping)

```text
Read CLAUDE.md. Two parts:
1. scripts/make_northwind.py: export a silver slice as "Northwind" with
   renamed columns, Fahrenheit temps, MM/DD/YYYY dates, numbers as
   strings with commas, 2 SMART columns missing, ~2% duplicates.
2. `halflife onboard --fleet --file`: profile the file, propose a column
   mapping with a confidence per field (name similarity + value-range
   checks, e.g. temps 80-130 => Fahrenheit), write it to
   mappings/<fleet>.yaml for me to review, then on --apply run clean ->
   features -> score. Missing attributes give null features and a lower
   coverage value stored with each score.
```

**3D — Deploy and README** (check: the live URL works with a demo login)

```text
Read CLAUDE.md. Add a small Dockerfile for workers (uv, non-root) and a
railway.json running ingest -> clean -> features -> score. Document
Vercel and Railway env vars in .env.example. Rewrite README: the customer
problem in 3 sentences, architecture diagram (Mermaid), the messy-data
fixes with counts from the latest quality report, the model results
table and cost curve, how to run locally, and a "Next" list (survival
model, upload UI, nightly cron, alerts, drift monitoring).
```

## Trim and review prompts

Run Trim whenever a diff looks longer than the ask deserves; run Review at the end of each day.

**Trim** (any time a diff feels bloated)

```text
Review the uncommitted diff against the code size rules in CLAUDE.md.
List every place that is longer than it needs to be: unused code,
abstractions used once, Python loops that could be one SQL query,
duplicate logic, redundant checks, comments restating code, tests that
check the same thing twice. Show the line count before and after for
each. Then make the cuts without changing behavior, and run the tests.
```

**Day-end review** (after 1E, 2D and 3D)

```text
Review today's commits as a skeptical staff engineer. Check: silent row
drops, time leakage, non-idempotent steps, secrets in code, missing edge
case tests, and anything I could not explain in an interview. List
issues by severity with file and line. Do not fix yet.
```

**If an ask stalls** (the agent loops or the plan grows)

```text
Stop. Summarize what works, what is failing, and the smallest next step.
Propose a version of this ask that is half the size.
```
