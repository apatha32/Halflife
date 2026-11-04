import Table from "@/components/Table";
import { session } from "@/lib/supabase";

type Report = {
  run_at: string; data_start: string; data_end: string; rows_in: number; rows_out: number;
  quarantined: Record<string, number>; quarantined_failures: number; resets_fixed: number;
  rows_rebased: number; schema_hashes: Record<string, number>; null_rate_change: Record<string, number>;
};

const n = (v: number) => v.toLocaleString("en-US");
const pairs = (o: Record<string, number>) => Object.entries(o).map(([k, v]) => ({ k, v: n(v) }));

export default async function DataQuality() {
  const { db, fleet } = await session();
  const { data } = await db.from("quality_reports").select("report").order("run_at", { ascending: false });
  const reports = (data ?? []).map((d) => d.report as Report);
  return (
    <div className="space-y-6">
      <div>
        <p className="font-mono text-xs tracking-widest text-neon uppercase">{fleet?.name}</p>
        <h1 className="mt-1 text-4xl font-semibold tracking-tight">Data quality</h1>
      </div>
      {reports.length === 0 && <p className="text-dim">No quality reports yet.</p>}
      {reports.map((r) => {
        const quarantined = Object.values(r.quarantined).reduce((a, b) => a + b, 0);
        const change = Object.entries(r.null_rate_change).sort((a, b) => Math.abs(b[1]) - Math.abs(a[1]))[0];
        return (
          <article key={r.run_at} className="space-y-4 border border-line shade p-4">
            <h2 className="font-mono text-xs tracking-wider text-dim uppercase">
              Run {r.run_at.replace("T", " ").slice(0, 16)} UTC / data {r.data_start} to {r.data_end}
            </h2>
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
              {[["rows in", r.rows_in], ["clean", r.rows_out], ["quarantined", quarantined], ["resets fixed", r.resets_fixed]].map(([k, v]) => (
                <div key={k} className="border border-line px-3 py-2">
                  <div className="font-mono text-xs tracking-wider text-dim uppercase">{k}</div>
                  <div className={`font-mono text-lg font-bold tabular-nums ${k === "clean" ? "text-neon" : k === "quarantined" ? "text-neon-600" : "text-soft"}`}>{n(Number(v))}</div>
                </div>
              ))}
            </div>
            <p className="text-sm text-dim">
              {r.quarantined_failures} failure rows quarantined. {n(r.rows_rebased)} rows rebased after counter resets.
              {change && ` Largest null-rate change vs previous run: ${change[0]} ${change[1] >= 0 ? "+" : ""}${(change[1] * 100).toFixed(1)} points.`}
            </p>
            <div className="grid gap-4 md:grid-cols-2">
              <Table columns={[{ key: "k", label: "Quarantine reason" }, { key: "v", label: "Rows", numeric: true }]} rows={pairs(r.quarantined)} />
              <Table columns={[{ key: "k", label: "Schema hash" }, { key: "v", label: "Rows", numeric: true }]} rows={pairs(r.schema_hashes)} />
            </div>
          </article>
        );
      })}
    </div>
  );
}
