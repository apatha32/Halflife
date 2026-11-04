import Link from "next/link";
import Table from "@/components/Table";
import { session } from "@/lib/supabase";
import Chart, { type Point } from "./Chart";

const HISTORY = [
  { key: "date", label: "Date" },
  { key: "smart_5", label: "Reallocated", numeric: true },
  { key: "smart_197", label: "Pending", numeric: true },
  { key: "smart_187", label: "Uncorrectable", numeric: true },
  { key: "smart_198", label: "Offline unc.", numeric: true },
  { key: "smart_194", label: "Temp °C", numeric: true },
];

export default async function Drive({ params }: { params: Promise<{ id: string }> }) {
  const id = decodeURIComponent((await params).id);
  const { db } = await session();
  const [{ data: drive }, { data: scores }, { data: history }] = await Promise.all([
    db.from("drives").select("model, manufacturer, capacity_tb").eq("drive_id", id).maybeSingle(),
    db.from("drive_scores").select("score_date, risk, rank, coverage, top_drivers").eq("drive_id", id).order("score_date", { ascending: false }),
    db.from("drive_history").select("date, smart_5, smart_187, smart_197, smart_198, smart_194").eq("drive_id", id).order("date"),
  ]);
  if (!drive) return <p>Drive not found in your fleet. <Link className="underline" href="/pull-list">Back to the pull list</Link></p>;
  const latest = scores?.[0];
  const drivers = (latest?.top_drivers ?? []) as string[];
  return (
    <div className="space-y-6">
      <div>
        <Link href="/pull-list" className="text-sm text-stone-500 dark:text-stone-400">← Pull list</Link>
        <h1 className="mt-1 text-2xl font-semibold break-all">{id}</h1>
        <p className="text-sm text-stone-600 dark:text-stone-300">
          {drive.manufacturer} {drive.model} · {Number(drive.capacity_tb).toFixed(0)} TB
          {latest && ` · rank ${latest.rank} on ${latest.score_date} · risk ${latest.risk.toFixed(3)}`}
        </p>
      </div>
      {drivers.length > 0 && (
        <section>
          <h2 className="mb-2 font-medium">Why this drive is flagged</h2>
          <ul className="list-disc space-y-1 pl-5 text-sm">
            {drivers.map((d) => <li key={d}>{d}. This pushes its failure risk up.</li>)}
          </ul>
          {latest && latest.coverage < 1 && (
            <p className="mt-2 text-sm text-stone-600 dark:text-stone-300">
              This drive reports {Math.round(latest.coverage * 100)}% of the SMART attributes the model uses, so its score rests on less evidence.
            </p>
          )}
        </section>
      )}
      {history && history.length > 0 ? (
        <>
          <Chart data={history as Point[]} scoreDate={latest?.score_date} risk={latest ? `risk ${latest.risk.toFixed(3)}` : ""} />
          <details className="text-sm">
            <summary className="cursor-pointer text-stone-600 dark:text-stone-300">Sensor history as a table</summary>
            <div className="mt-2">
              <Table columns={HISTORY} rows={[...history].reverse()} />
            </div>
          </details>
        </>
      ) : (
        <p className="text-sm text-stone-600 dark:text-stone-300">No sensor history stored for this drive (history is kept for the top 1,000 ranked drives).</p>
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
