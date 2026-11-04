import Link from "next/link";
import { ViewTransition } from "react";
import Table from "@/components/Table";
import { session } from "@/lib/supabase";
import Chart, { type Point } from "./Chart";

const HISTORY = [
  { key: "date", label: "Date" },
  { key: "smart_5", label: "Reallocated", numeric: true },
  { key: "smart_197", label: "Pending", numeric: true },
  { key: "smart_187", label: "Uncorrectable", numeric: true },
  { key: "smart_198", label: "Offline unc.", numeric: true },
  { key: "smart_194", label: "Temp C", numeric: true },
];

export default async function Drive({ params }: { params: Promise<{ id: string }> }) {
  const id = decodeURIComponent((await params).id);
  const { db } = await session();
  const [{ data: drive }, { data: scores }, { data: history }] = await Promise.all([
    db.from("drives").select("model, manufacturer, capacity_tb").eq("drive_id", id).maybeSingle(),
    db.from("drive_scores").select("score_date, risk, rank, coverage, top_drivers").eq("drive_id", id).order("score_date", { ascending: false }),
    db.from("drive_history").select("date, smart_5, smart_187, smart_197, smart_198, smart_194").eq("drive_id", id).order("date"),
  ]);
  if (!drive) return <p>Drive not found in your fleet. <Link className="text-neon underline" href="/pull-list">Back to the pull list</Link></p>;
  const latest = scores?.[0];
  const drivers = (latest?.top_drivers ?? []) as string[];
  return (
    <div className="space-y-8">
      <div>
        <Link href="/pull-list" className="font-mono text-xs tracking-wider text-dim uppercase hover:text-neon">&lt; pull list</Link>
        <ViewTransition name={`drive-${id}`} share="morph" default="none">
          <h1 className="mt-2 font-mono text-3xl font-bold break-all">{id}</h1>
        </ViewTransition>
        <p className="mt-1 text-sm text-dim">
          {drive.manufacturer} {drive.model} / {Number(drive.capacity_tb).toFixed(0)} TB
        </p>
        {latest && (
          <div className="mt-4 flex flex-wrap gap-3">
            {[["rank", `#${latest.rank}`], ["risk", latest.risk.toFixed(3)], ["scored", latest.score_date]].map(([k, v]) => (
              <div key={k} className="border border-line shade px-4 py-2">
                <div className="font-mono text-xs tracking-wider text-dim uppercase">{k}</div>
                <div className={`font-mono text-xl font-bold ${k === "scored" ? "text-soft" : "glow text-neon"}`}>{v}</div>
              </div>
            ))}
          </div>
        )}
      </div>
      {drivers.length > 0 && (
        <section>
          <h2 className="mb-3 font-mono text-xs tracking-wider text-dim uppercase">Why this drive is flagged</h2>
          <ol className="space-y-2 text-sm">
            {drivers.map((d, i) => (
              <li key={d} className="rise flex gap-3 border-l-2 border-neon bg-gradient-to-r from-neon-900/50 via-panel to-panel px-3 py-2" style={{ animationDelay: `${i * 120}ms` }}>
                <span className="font-mono text-neon-300">0{i + 1}</span>
                <span>{d}. This pushes its failure risk up.</span>
              </li>
            ))}
          </ol>
          {latest && latest.coverage < 1 && (
            <p className="mt-3 text-sm text-dim">
              This drive reports {Math.round(latest.coverage * 100)}% of the SMART attributes the model uses, so its score rests on less evidence.
            </p>
          )}
        </section>
      )}
      {history && history.length > 0 ? (
        <>
          <Chart data={history as Point[]} scoreDate={latest?.score_date} risk={latest ? `risk ${latest.risk.toFixed(3)}` : ""} />
          <details className="text-sm">
            <summary className="cursor-pointer text-dim hover:text-neon">Sensor history as a table</summary>
            <div className="mt-2"><Table columns={HISTORY} rows={[...history].reverse()} /></div>
          </details>
        </>
      ) : (
        <p className="text-sm text-dim">No sensor history stored for this drive (history is kept for the top 1,000 ranked drives).</p>
      )}
      {scores && scores.length > 1 && (
        <Table
          columns={[{ key: "score_date", label: "Scored" }, { key: "rank", label: "Rank", numeric: true }, { key: "risk", label: "Risk", numeric: true }]}
          rows={scores.map((s) => ({ ...s, risk: s.risk.toFixed(3) }))}
        />
      )}
    </div>
  );
}
