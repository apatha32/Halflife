import Link from "next/link";
import { session } from "@/lib/supabase";
import { STATUS } from "../page";
import { approve } from "./actions";

const TARGETS: [string, string][] = [
  ["drive_id", "Drive serial (required)"], ["date", "Date (required)"], ["model", "Model (required)"],
  ["capacity_tb", "Capacity"], ["failure", "Failed flag (0/1)"], ["smart_5", "Reallocated sectors (SMART 5)"],
  ["smart_9", "Power-on hours (SMART 9)"], ["smart_12", "Power cycles (SMART 12)"],
  ["smart_187", "Reported uncorrectable (SMART 187)"], ["smart_188", "Command timeouts (SMART 188)"],
  ["smart_194", "Temperature (SMART 194)"], ["smart_197", "Pending sectors (SMART 197)"],
  ["smart_198", "Offline uncorrectable (SMART 198)"], ["smart_199", "CRC errors (SMART 199)"],
];
const FORMATS = ["%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y"];

type Mapping = {
  columns: Record<string, { source: string; confidence: number | string; transform?: string }>;
  sources: string[]; date_format: string;
};
type Result = { rows_in: number; rows_out: number; quarantined: Record<string, number>; parse_failures: Record<string, number>; data_end: string; scored: number };

const field = "w-full border border-line bg-raised px-2 py-1.5 font-mono text-sm outline-none focus:border-neon-600";

export default async function Review({ params, searchParams }: { params: Promise<{ id: string }>; searchParams: Promise<{ error?: string }> }) {
  const [{ id }, { error }] = await Promise.all([params, searchParams]);
  const { db, user } = await session();
  const { data: u } = await db.from("uploads").select("fleet_id, filename, status, mapping, result, error").eq("id", id).maybeSingle();
  if (!u) return <p>Upload not found. <Link className="text-neon underline" href="/upload">Back to uploads</Link></p>;
  const { data: member } = await db.from("memberships").select("role").eq("fleet_id", u.fleet_id).eq("user_id", user.id).maybeSingle();
  const m = u.mapping as Mapping | null, r = u.result as Result | null;
  const n = (v: number) => v.toLocaleString("en-US");
  return (
    <div className="space-y-6">
      <div>
        <Link href="/upload" className="font-mono text-xs tracking-wider text-dim uppercase hover:text-neon">&lt; uploads</Link>
        <h1 className="mt-2 font-mono text-2xl font-bold break-all">{u.filename}</h1>
        <p className={`mt-1 text-sm ${STATUS[u.status][1]}`}>{STATUS[u.status][0]}</p>
        {u.status === "approved" && <p className="mt-1 text-sm text-dim">Scores appear after the next processing run, within about 10 minutes.</p>}
        {u.error && <p className="mt-2 text-sm text-paper">Error: {u.error}</p>}
        {error && <p className="mt-2 text-sm text-paper">{error}</p>}
      </div>
      {r && (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          {[["rows in", n(r.rows_in)], ["clean", n(r.rows_out)], ["drives scored", n(r.scored)], ["latest day", r.data_end]].map(([k, v]) => (
            <div key={k} className="shade border border-line px-3 py-2">
              <div className="font-mono text-xs tracking-wider text-dim uppercase">{k}</div>
              <div className="font-mono text-lg font-bold text-neon">{v}</div>
            </div>
          ))}
          <p className="col-span-full text-sm text-dim">
            Quarantined: {Object.entries(r.quarantined).map(([k, v]) => `${k} ${n(v)}`).join(", ") || "none"}.
            Values that could not be parsed: {Object.entries(r.parse_failures).map(([k, v]) => `${k} ${n(v)}`).join(", ") || "none"}.{" "}
            <Link className="text-neon underline" href="/pull-list">Open the pull list</Link>
          </p>
        </div>
      )}
      {m && u.status === "needs_review" && member?.role === "admin" && (
        <form action={approve.bind(null, id)} className="space-y-4">
          <h2 className="font-mono text-xs tracking-wider text-dim uppercase">Proposed column mapping</h2>
          <div className="grid gap-3 sm:grid-cols-2">
            {TARGETS.map(([t, label]) => {
              const c = m.columns[t];
              return (
                <label key={t} className="shade block border border-line p-3">
                  <span className="flex justify-between gap-2 text-sm">
                    {label}
                    {c && <span className={`font-mono text-xs ${Number(c.confidence) >= 0.8 ? "text-neon" : "text-neon-300"}`}>{Math.round(Number(c.confidence) * 100)}%</span>}
                  </span>
                  <select name={`t:${t}`} defaultValue={c?.source ?? ""} className={`mt-2 ${field}`}>
                    <option value="">Not in this file</option>
                    {m.sources.map((s) => <option key={s} value={s}>{s}</option>)}
                  </select>
                </label>
              );
            })}
          </div>
          <div className="grid gap-3 sm:grid-cols-3">
            {[
              ["temp_unit", "Temperature unit", m.columns.smart_194?.transform ? "F" : "C", [["C", "Celsius"], ["F", "Fahrenheit"]]],
              ["capacity_unit", "Capacity unit", m.columns.capacity_tb?.transform ? "bytes" : "TB", [["TB", "Terabytes"], ["bytes", "Bytes"]]],
              ["date_format", "Date format", m.date_format, FORMATS.map((f) => [f, f.replaceAll("%Y", "YYYY").replaceAll("%m", "MM").replaceAll("%d", "DD")])],
            ].map(([name, label, value, opts]) => (
              <label key={name as string} className="block text-sm">
                {label as string}
                <select name={name as string} defaultValue={value as string} className={`mt-2 ${field}`}>
                  {(opts as string[][]).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
                </select>
              </label>
            ))}
          </div>
          <button className="neon-btn border border-neon px-4 py-2 text-neon">Approve and score</button>
        </form>
      )}
    </div>
  );
}
