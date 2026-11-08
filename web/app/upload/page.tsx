import Link from "next/link";
import Table from "@/components/Table";
import { session } from "@/lib/supabase";
import Uploader from "./Uploader";

export const STATUS: Record<string, [string, string]> = {
  uploaded: ["Uploaded, waiting for a mapping", "text-soft"],
  needs_review: ["Mapping ready for review", "text-neon glow"],
  approved: ["Approved, waiting to be scored", "text-neon-300"],
  processing: ["Scoring now", "text-neon-300"],
  scored: ["Scored", "text-neon"],
  failed: ["Failed", "text-paper"],
};

export default async function Uploads() {
  const { db, user, fleet } = await session();
  if (!fleet) return <p>Your account is not a member of any fleet yet.</p>;
  const [{ data: member }, { data }] = await Promise.all([
    db.from("memberships").select("role").eq("fleet_id", fleet.id).eq("user_id", user.id).maybeSingle(),
    db.from("uploads").select("id, filename, status, created_at").order("created_at", { ascending: false }),
  ]);
  return (
    <div className="space-y-6">
      <div>
        <p className="font-mono text-xs tracking-widest text-neon uppercase">{fleet.name}</p>
        <h1 className="mt-1 text-4xl font-semibold tracking-tight">Upload drive data</h1>
        <p className="mt-1 text-sm text-dim">
          Upload a daily SMART export. Halflife proposes how its columns map to drive fields, you review it, and the drives are scored.
        </p>
      </div>
      {member?.role === "admin" ? (
        <Uploader fleetId={fleet.id} />
      ) : (
        <p className="border border-line px-4 py-3 text-sm text-dim">This is a view-only account, so uploads are turned off. Fleet admins can upload.</p>
      )}
      {(data ?? []).length > 0 && (
        <Table
          columns={[{ key: "filename", label: "File" }, { key: "status", label: "Status" }, { key: "when", label: "Uploaded", wide: true }]}
          rows={(data ?? []).map((u) => ({
            filename: <Link className="font-mono underline decoration-line underline-offset-4 hover:text-neon" href={`/upload/${u.id}`}>{u.filename}</Link>,
            status: <span className={STATUS[u.status][1]}>{STATUS[u.status][0]}</span>,
            when: u.created_at.replace("T", " ").slice(0, 16),
          }))}
        />
      )}
    </div>
  );
}
