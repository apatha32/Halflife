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
      <h1 className="text-2xl font-semibold">Data quality — {fleet?.name}</h1>
      {reports.length === 0 && <p>No quality reports yet.</p>}
      {reports.map((r) => (
        <article key={r.run_at} className="space-y-3 rounded border border-stone-200 bg-white p-4 dark:border-stone-700 dark:bg-stone-950">
          <h2 className="font-medium">Run {r.run_at.replace("T", " ").slice(0, 16)} UTC · data {r.data_start} to {r.data_end}</h2>
          <p className="text-sm">
            {n(r.rows_in)} rows in → {n(r.rows_out)} clean + {n(Object.values(r.quarantined).reduce((a, b) => a + b, 0))} quarantined
            ({r.quarantined_failures} failure rows). {n(r.resets_fixed)} counter resets fixed ({n(r.rows_rebased)} rows rebased).
          </p>
          <div className="grid gap-4 md:grid-cols-2">
            <Table columns={[{ key: "k", label: "Quarantine reason" }, { key: "v", label: "Rows", numeric: true }]} rows={pairs(r.quarantined)} />
            <Table columns={[{ key: "k", label: "Schema hash" }, { key: "v", label: "Rows", numeric: true }]} rows={pairs(r.schema_hashes)} />
          </div>
          {Object.keys(r.null_rate_change).length > 0 && (
            <p className="text-sm text-stone-600 dark:text-stone-300">
              Largest null-rate change vs previous run:{" "}
              {(([k, v]) => `${k} ${v >= 0 ? "+" : ""}${(v * 100).toFixed(1)} points`)(
                Object.entries(r.null_rate_change).sort((a, b) => Math.abs(b[1]) - Math.abs(a[1]))[0],
              )}
            </p>
          )}
        </article>
      ))}
    </div>
  );
}
