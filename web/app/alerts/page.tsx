import Link from "next/link";
import Table from "@/components/Table";
import { session } from "@/lib/supabase";

type Alert = { drive_id: string; score_date: string; kind: string; rank: number; prev_rank: number | null };

export default async function Alerts() {
  const { db, fleet } = await session();
  const { data } = await db
    .from("alerts")
    .select("drive_id, score_date, kind, rank, prev_rank")
    .order("score_date", { ascending: false })
    .order("rank")
    .limit(200);
  const alerts = (data ?? []) as Alert[];
  return (
    <div className="space-y-4">
      <div>
        <p className="font-mono text-xs tracking-widest text-neon uppercase">{fleet?.name}</p>
        <h1 className="mt-1 text-4xl font-semibold tracking-tight">Alerts</h1>
        <p className="mt-1 text-sm text-dim">
          A drive alerts when it enters the weekly pull list or jumps 100+ ranks toward it since the previous scoring day.
        </p>
      </div>
      {alerts.length === 0 ? (
        <p className="text-dim">No alerts yet. They appear after the second scoring day.</p>
      ) : (
        <Table
          columns={[
            { key: "score_date", label: "Day", wide: true },
            { key: "drive_id", label: "Drive" },
            { key: "what", label: "What happened" },
            { key: "rank", label: "Rank", numeric: true },
          ]}
          rows={alerts.map((a) => ({
            ...a,
            drive_id: (
              <Link className="font-mono underline decoration-line underline-offset-4 hover:text-neon hover:decoration-neon" href={`/drives/${encodeURIComponent(a.drive_id)}`}>
                {a.drive_id}
              </Link>
            ),
            what: a.kind === "entered_top_k"
              ? <span className="text-neon">Entered the pull list{a.prev_rank ? ` (was #${a.prev_rank.toLocaleString("en-US")})` : " (new drive)"}</span>
              : <span className="text-neon-300">Rose from #{a.prev_rank?.toLocaleString("en-US")}</span>,
          }))}
        />
      )}
    </div>
  );
}
