"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { browserClient } from "@/lib/supabase-browser";

const MAX = 20 * 1024 * 1024;

export default function Uploader({ fleetId }: { fleetId: string }) {
  const router = useRouter();
  const [status, setStatus] = useState("");

  async function send(file: File) {
    if (!file.name.toLowerCase().endsWith(".csv")) return setStatus("Choose a .csv file.");
    if (file.size > MAX) return setStatus("Files are limited to 20 MB.");
    setStatus(`Uploading ${file.name}...`);
    const db = browserClient();
    const path = `${fleetId}/${Date.now()}-${file.name.replace(/[^\w.-]+/g, "_")}`;
    const up = await db.storage.from("uploads").upload(path, file, { contentType: "text/csv" });
    const row = up.error ? up : await db.from("uploads").insert({ fleet_id: fleetId, path, filename: file.name });
    setStatus(row.error ? `Upload failed: ${row.error.message}` : `${file.name} uploaded. A column mapping will be proposed shortly.`);
    router.refresh();
  }

  return (
    <label className="neon-btn block cursor-pointer border border-dashed border-neon-700 px-4 py-8 text-center">
      <input type="file" accept=".csv,text/csv" className="sr-only" onChange={(e) => e.target.files?.[0] && send(e.target.files[0])} />
      <span className="font-mono text-sm">Choose a CSV export (up to 20 MB)</span>
      {status && <span className="mt-2 block text-sm">{status}</span>}
    </label>
  );
}
