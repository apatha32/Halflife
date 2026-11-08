# Deploy: steps to run yourself

Order: Supabase first (the other two need its URL and keys), then Railway, then Vercel.

## 1. Supabase (hosted)

```sh
supabase login
supabase projects create halflife --org-id <org-id> --region us-east-1 --db-password '<strong-password>'
supabase link --project-ref <project-ref>
supabase db push --include-seed        # migration + demo fleets/users (password halflife-demo)
```

Dashboard > Authentication > URL Configuration: Site URL = `https://<your-vercel-domain>`, add
`https://<your-vercel-domain>/auth/callback` to Redirect URLs (magic links). Copy the project URL,
anon key and service-role key from Project Settings > API.

The migrations also create the private `uploads` storage bucket (CSV only, 20 MB) and its access
rules. Seeded demo users have a public password, so the seed makes them viewers: they can read the
two demo fleets but cannot upload. To give a real user upload rights, add them in Authentication >
Users and insert a membership:
`insert into memberships (user_id, fleet_id, role) values ('<user id>', '<fleet id>', 'admin');`

## 2. Railway (workers job)

```sh
railway login
railway init --name halflife-workers          # from the repo root; railway.json builds workers/Dockerfile
railway volume add --mount-path /app/data
railway variables \
  --set B2_ENDPOINT=s3.us-west-004.backblazeb2.com --set B2_REGION=us-west-004 \
  --set B2_BUCKET=drivestats-iceberg --set B2_PREFIX=drivestats \
  --set B2_KEY_ID=<public key id> --set B2_APP_KEY=<public app key> \
  --set SUPABASE_URL=https://<project-ref>.supabase.co --set SUPABASE_SERVICE_ROLE_KEY=<service-role key> \
  --set INGEST_START=2024-01-01 --set SAMPLE_PCT=10 --set RAILWAY_RUN_UID=0
# optional: --set SLACK_WEBHOOK_URL=<incoming webhook> to post new alerts
railway up
```

`RAILWAY_RUN_UID=0` is needed because Railway mounts volumes as root and the image runs as a
non-root user. The job runs `halflife nightly` every day at 06:00 UTC (`cronSchedule` in
railway.json): it re-ingests the newest month already on the volume plus anything newer that
Backblaze has published, rebuilds silver and gold, scores the newest day, prunes stale scores and
raises alerts. The first run starts from INGEST_START, needs up to ~8 GB RAM and a few GB of volume,
and takes ~15-20 minutes; later runs are a few minutes. Backblaze publishes Drive Stats quarterly,
so most nights re-score the same day and create no new alerts.

Second Railway service for customer uploads (same repo and image, no volume needed):

```sh
railway add --service halflife-uploads
railway variables --service halflife-uploads \
  --set SUPABASE_URL=https://<project-ref>.supabase.co --set SUPABASE_SERVICE_ROLE_KEY=<service-role key> \
  --set RAILWAY_RUN_UID=0
```

In that service's settings, set the start command to `halflife uploads`, the cron schedule to
`*/10 * * * *` and the restart policy to Never (railway.json describes the nightly service only).
Each run takes seconds when nothing is waiting.

## 3. Vercel (web)

```sh
cd web
vercel link                       # set the project's Root Directory to web/
vercel env add NEXT_PUBLIC_SUPABASE_URL production        # https://<project-ref>.supabase.co
vercel env add NEXT_PUBLIC_SUPABASE_ANON_KEY production   # anon key only
vercel env add DEMO_PASSWORD production                   # halflife-demo (shows demo buttons)
vercel --prod
```

Check: open `https://<your-vercel-domain>/login`, click "Demo: Acme Storage", and confirm the pull
list shows scores dated 2025-12-31 once the Railway job has finished.
