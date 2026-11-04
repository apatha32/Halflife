import Link from "next/link";
import { ViewTransition } from "react";
import Table from "@/components/Table";
import { session } from "@/lib/supabase";

const PAGE = 25;
const tier = (rank: number) =>
  rank <= 3 ? "glow font-bold text-neon" : rank <= 10 ? "text-neon-300" : rank <= 50 ? "text-neon-600" : "text-soft";
export const COLUMNS = [
  { key: "rank", label: "#", numeric: true },
  { key: "drive_id", label: "Drive" },
  { key: "model", label: "Model", wide: true },
  { key: "age", label: "Age (yrs)", numeric: true, wide: true },
  { key: "risk", label: "Risk", numeric: true },
  { key: "top_driver", label: "Top driver" },
];

export type PullRow = {
  drive_id: string; model: string; age_days: number | null; risk: number;
  rank: number; top_driver: string | null; coverage: number; score_date: string;
};

export default async function PullList({ searchParams }: { searchParams: Promise<{ page?: string }> }) {
  const page = Math.max(1, Number((await searchParams).page) || 1);
  const { db, fleet } = await session();
  if (!fleet) return <p>Your account is not a member of any fleet yet.</p>;
  const { data, count } = await db
    .rpc("pull_list", { fid: fleet.id, k: 500 }, { count: "exact" })
    .range((page - 1) * PAGE, page * PAGE - 1);
  const rows = (data ?? []) as PullRow[];
  const pages = Math.max(1, Math.ceil((count ?? 0) / PAGE));
  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="font-mono text-xs tracking-widest text-neon uppercase">{fleet.name}</p>
          <h1 className="mt-1 text-4xl font-semibold tracking-tight">Pull list</h1>
          <p className="mt-1 text-sm text-dim">
            Riskiest drives {rows[0] ? `scored ${rows[0].score_date}` : ""}. Risk ranks drives; it is not a calibrated probability.
          </p>
        </div>
        <a href="/pull-list/export" className="neon-btn border border-neon px-3 py-1.5 text-sm text-neon">Export CSV</a>
      </div>
      <Table
        columns={COLUMNS}
        rows={rows.map((r) => ({
          ...r,
          rank: <span className={tier(r.rank)}>{r.rank}</span>,
          drive_id: <Link className="underline decoration-line underline-offset-4 transition-colors hover:text-neon hover:decoration-neon" href={`/drives/${encodeURIComponent(r.drive_id)}`}>
            <ViewTransition name={`drive-${r.drive_id}`} share="morph" default="none"><span className="font-mono">{r.drive_id}</span></ViewTransition>
          </Link>,
          age: r.age_days == null ? "n/a" : (r.age_days / 365).toFixed(1),
          risk: <span className={tier(r.rank)}>{r.risk.toFixed(3)}</span>,
          top_driver: (r.top_driver ?? "n/a") + (r.coverage < 1 ? ` (coverage ${Math.round(r.coverage * 100)}%)` : ""),
        }))}
      />
      <div className="flex items-center justify-between text-sm">
        {page > 1 ? <Link className="font-mono hover:text-neon" href={`?page=${page - 1}`}>&lt; prev</Link> : <span />}
        <span className="font-mono text-dim">page {page} / {pages}</span>
        {page < pages ? <Link className="font-mono hover:text-neon" href={`?page=${page + 1}`}>next &gt;</Link> : <span />}
      </div>
    </div>
  );
}
