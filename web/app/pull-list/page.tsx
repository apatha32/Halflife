import Link from "next/link";
import Table from "@/components/Table";
import { session } from "@/lib/supabase";

const PAGE = 25;
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
          <h1 className="text-2xl font-semibold">Pull list — {fleet.name}</h1>
          <p className="text-sm text-stone-600 dark:text-stone-300">
            Riskiest drives {rows[0] ? `scored ${rows[0].score_date}` : ""}. Risk ranks drives; it is not a calibrated probability.
          </p>
        </div>
        <a href="/pull-list/export" className="rounded border border-stone-300 px-3 py-1.5 text-sm dark:border-stone-600">Export CSV</a>
      </div>
      <Table
        columns={COLUMNS}
        rows={rows.map((r) => ({
          ...r,
          drive_id: <Link className="underline" href={`/drives/${encodeURIComponent(r.drive_id)}`}>{r.drive_id}</Link>,
          age: r.age_days == null ? "—" : (r.age_days / 365).toFixed(1),
          risk: r.risk.toFixed(3),
          top_driver: (r.top_driver ?? "—") + (r.coverage < 1 ? ` (coverage ${Math.round(r.coverage * 100)}%)` : ""),
        }))}
      />
      <div className="flex items-center justify-between text-sm">
        {page > 1 ? <Link href={`?page=${page - 1}`}>← Previous</Link> : <span />}
        <span className="text-stone-500 dark:text-stone-400">Page {page} of {pages}</span>
        {page < pages ? <Link href={`?page=${page + 1}`}>Next →</Link> : <span />}
      </div>
    </div>
  );
}
