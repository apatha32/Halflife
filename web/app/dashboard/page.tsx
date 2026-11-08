import Link from "next/link";
import CountUp from "@/components/CountUp";
import { pct } from "@/lib/format";
import { session } from "@/lib/supabase";
import type { PullRow } from "../pull-list/page";
import RiskCliff from "./RiskCliff";

const K = 50;
const TIERS = ["10% or more", "1 to 10%", "0.1 to 1%", "under 0.1%"];
const PLAIN: Record<string, string> = {
  smart_9: "power-on hours", age_days: "drive age", smart_12: "power cycles", capacity_tb: "capacity",
  smart_194: "temperature", temp_mean_7d: "temperature", smart_5: "reallocated sectors", smart_197: "pending sectors",
};

type Summary = {
  day: string | null; drives: number; expected_7d: number; expected_30d: number; expected_90d: number;
  expected_topk: number; tiers: number[]; alerts: number; entered: number;
};

function Card({ label, children, sub, i }: { label: string; children: React.ReactNode; sub: React.ReactNode; i: number }) {
  return (
    <div className="rise shade group relative overflow-hidden border border-line p-5 transition-colors duration-500 hover:border-neon-800" style={{ animationDelay: `${i * 90}ms` }}>
      <div className="pointer-events-none absolute -top-16 -right-16 h-32 w-32 rounded-full bg-neon/5 blur-2xl transition-opacity duration-700 group-hover:bg-neon/10" />
      <div className="font-mono text-xs tracking-wider text-dim uppercase">{label}</div>
      <div className="mt-2 font-mono text-4xl font-semibold tracking-tight tabular-nums">{children}</div>
      <div className="mt-2 text-sm text-soft">{sub}</div>
    </div>
  );
}

export default async function Dashboard() {
  const { db, fleet } = await session();
  if (!fleet) return <p>Your account is not a member of any fleet yet.</p>;
  const [{ data: summary }, { data: top }, { data: alerts }, { data: reports }] = await Promise.all([
    db.rpc("fleet_summary", { fid: fleet.id, k: K }),
    db.rpc("pull_list", { fid: fleet.id, k: 500 }),
    db.from("alerts").select("drive_id, kind, rank, prev_rank, score_date").order("score_date", { ascending: false }).order("rank").limit(5),
    db.from("quality_reports").select("report").order("run_at", { ascending: false }).limit(1),
  ]);
  const s = summary as Summary;
  if (!s?.day) return <p className="text-dim">No scores yet for {fleet.name}. They appear after the first scoring run.</p>;
  const bars = (top ?? []) as PullRow[];
  const rest = bars.slice(K).reduce((a, b) => a + b.risk, 0);
  const report = reports?.[0]?.report as { rows_in: number; quarantined: Record<string, number>; model_health?: { drift_psi: Record<string, number> } } | undefined;
  const drifting = Object.entries(report?.model_health?.drift_psi ?? {}).filter(([, v]) => v >= 0.25).map(([f]) => PLAIN[f] ?? f.replaceAll("_", " "));
  const quarantined = Object.values(report?.quarantined ?? {}).reduce((a, b) => a + b, 0);
  return (
    <div className="space-y-8">
      <header className="rise">
        <p className="font-mono text-xs tracking-widest text-neon uppercase">{fleet.name} / scored {s.day}</p>
        <h1 className="mt-2 max-w-3xl text-3xl leading-tight font-semibold tracking-tight sm:text-4xl">
          Expect about {Math.round(s.expected_30d)} failures in the next 30 days across {s.drives.toLocaleString("en-US")} drives.{" "}
          <span className="text-neon">This week&apos;s {K} pulls cover {s.expected_topk.toFixed(1)} of them.</span>
        </h1>
      </header>

      <section className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4" aria-label="Fleet summary">
        <Card i={0} label="Expected failures, 30 days" sub={<>7 days {s.expected_7d.toFixed(1)} / 90 days {Math.round(s.expected_90d)}</>}>
          <CountUp value={s.expected_30d} decimals={1} />
        </Card>
        <Card i={1} label="Pull list coverage" sub={<>{K} drives, {pct(K / s.drives)} of the fleet</>}>
          <span className="text-neon"><CountUp value={(100 * s.expected_topk) / s.expected_30d} decimals={0} suffix="%" /></span>
        </Card>
        <Card i={2} label="New alerts" sub={<>{s.entered} entered the pull list, {s.alerts - s.entered} jumped in rank</>}>
          <CountUp value={s.alerts} />
        </Card>
        <Card
          i={3}
          label="Data and model"
          sub={<>{drifting.length ? `Drifting: ${[...new Set(drifting)].join(", ")}` : "No feature drift"}. {quarantined.toLocaleString("en-US")} rows quarantined.</>}
        >
          <span className={drifting.length ? "text-neon-300" : "text-neon"}>{drifting.length ? "Watch" : "Healthy"}</span>
        </Card>
      </section>

      <section className="rise" style={{ animationDelay: "360ms" }}>
        <RiskCliff bars={bars} k={K} pulled={s.expected_topk} rest={rest} />
        <div className="mt-3 grid grid-cols-2 gap-3 sm:grid-cols-4">
          {s.tiers.map((n, i) => (
            <div key={TIERS[i]} className="border-l-2 py-1 pl-3" style={{ borderColor: ["#39ff14", "#26c80c", "#125f06", "#3a3a3a"][i] }}>
              <div className="font-mono text-lg font-semibold tabular-nums">{n.toLocaleString("en-US")}</div>
              <div className="text-xs text-dim">drives at {TIERS[i]} risk</div>
            </div>
          ))}
        </div>
      </section>

      <section className="grid gap-3 lg:grid-cols-2">
        <div className="rise shade min-w-0 border border-line p-5" style={{ animationDelay: "450ms" }}>
          <div className="mb-3 flex items-baseline justify-between">
            <h2 className="font-mono text-xs tracking-wider text-dim uppercase">Pull first</h2>
            <Link href="/pull-list" className="text-sm text-neon-300 hover:text-neon">Full pull list</Link>
          </div>
          <ol className="divide-y divide-line">
            {bars.slice(0, 5).map((b) => (
              <li key={b.drive_id}>
                <Link href={`/drives/${encodeURIComponent(b.drive_id)}`} className="flex items-center gap-3 py-2.5 hover:text-neon">
                  <span className="w-8 font-mono text-sm text-neon">#{b.rank}</span>
                  <span className="min-w-0 flex-1">
                    <span className="block font-mono text-sm">{b.drive_id}</span>
                    <span className="block truncate text-xs text-dim">{b.top_driver}</span>
                  </span>
                  <span className="font-mono text-sm tabular-nums">{pct(b.risk)}</span>
                </Link>
              </li>
            ))}
          </ol>
        </div>
        <div className="rise shade min-w-0 border border-line p-5" style={{ animationDelay: "540ms" }}>
          <div className="mb-3 flex items-baseline justify-between">
            <h2 className="font-mono text-xs tracking-wider text-dim uppercase">Latest alerts</h2>
            <Link href="/alerts" className="text-sm text-neon-300 hover:text-neon">All alerts</Link>
          </div>
          {(alerts ?? []).length === 0 ? (
            <p className="text-sm text-dim">No alerts yet. They appear after the second scoring day.</p>
          ) : (
            <ul className="divide-y divide-line">
              {(alerts ?? []).map((a) => (
                <li key={a.drive_id + a.kind}>
                  <Link href={`/drives/${encodeURIComponent(a.drive_id)}`} className="flex items-center gap-3 py-2.5 hover:text-neon">
                    <span className="font-mono text-sm">{a.drive_id}</span>
                    <span className="min-w-0 flex-1 truncate text-xs text-dim">
                      {a.kind === "entered_top_k" ? "entered the pull list" : `rose from #${a.prev_rank?.toLocaleString("en-US")}`}
                    </span>
                    <span className="font-mono text-sm text-neon">#{a.rank}</span>
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </div>
      </section>
    </div>
  );
}
