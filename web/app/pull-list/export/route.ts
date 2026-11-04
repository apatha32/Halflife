import { session } from "@/lib/supabase";
import type { PullRow } from "../page";

const quote = (v: unknown) => `"${String(v ?? "").replaceAll('"', '""')}"`;

export async function GET() {
  const { db, fleet } = await session();
  const { data } = await db.rpc("pull_list", { fid: fleet?.id, k: 500 });
  const rows = (data ?? []) as PullRow[];
  const cols = ["rank", "drive_id", "model", "age_days", "risk", "top_driver", "coverage", "score_date"] as const;
  const csv = [cols.join(","), ...rows.map((r) => cols.map((c) => quote(r[c])).join(","))].join("\n");
  return new Response(csv, {
    headers: { "Content-Type": "text/csv", "Content-Disposition": 'attachment; filename="pull-list.csv"' },
  });
}
