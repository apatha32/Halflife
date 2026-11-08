import Table from "@/components/Table";
import { session } from "@/lib/supabase";

type Report = {
  run_at: string; data_start: string; data_end: string; rows_in: number; rows_out: number;
  quarantined: Record<string, number>; quarantined_failures: number; resets_fixed: number;
  rows_rebased: number; schema_hashes: Record<string, number>; null_rate_change: Record<string, number>;
  parse_failures?: Record<string, number>;
  model_health?: {
    model_version: string; drift_date: string; drift_psi: Record<string, number>; backtest_date: string;
    backtest: Record<string, number>;
  };
};

const drift = (v: number) => (v < 0.1 ? ["stable", "text-neon"] : v < 0.25 ? ["watch", "text-neon-300"] : ["drifting", "text-paper"]);

function Health({ h }: { h: NonNullable<Report["model_health"]> }) {
  const find = (prefix: string) => Object.entries(h.backtest).find(([k]) => k.startsWith(prefix))!;
  const [prec, rec] = [find("precision"), find("recall")];
  return (
    <div className="space-y-3 border-t border-line pt-4">
      <h3 className="font-mono text-xs tracking-wider text-dim uppercase">Model health / {h.model_version}</h3>
      <p className="text-sm text-soft">
        Backtest on {h.backtest_date}: {(prec[1] * 100).toFixed(1)}% of the weekly pull list failed within 30 days and it caught{" "}
        {(rec[1] * 100).toFixed(1)}% of failures. Expected {h.backtest.expected_failures} failures, observed {h.backtest.observed_failures}.
      </p>
      <p className="text-sm text-dim">
        Feature drift on {h.drift_date} versus training data (PSI: under 0.1 stable, 0.1 to 0.25 watch, over 0.25 drifting).
      </p>
      <Table
        columns={[{ key: "f", label: "Feature" }, { key: "v", label: "PSI", numeric: true }, { key: "s", label: "Status" }]}
        rows={Object.entries(h.drift_psi).sort((a, b) => b[1] - a[1]).map(([f, v]) => {
          const [label, cls] = drift(v);
          return { f, v: v.toFixed(3), s: <span className={cls}>{label}</span> };
        })}
      />
    </div>
  );
}

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
              {r.parse_failures &&
                ` Values that could not be parsed (stored as empty): ${Object.entries(r.parse_failures).map(([k, v]) => `${k} ${n(v)}`).join(", ") || "none"}.`}
            </p>
            <div className="grid gap-4 md:grid-cols-2">
              <Table columns={[{ key: "k", label: "Quarantine reason" }, { key: "v", label: "Rows", numeric: true }]} rows={pairs(r.quarantined)} />
              <Table columns={[{ key: "k", label: "Schema hash" }, { key: "v", label: "Rows", numeric: true }]} rows={pairs(r.schema_hashes)} />
            </div>
            {r.model_health && <Health h={r.model_health} />}
          </article>
        );
      })}
    </div>
  );
}
