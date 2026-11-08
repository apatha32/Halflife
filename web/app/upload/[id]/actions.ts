"use server";

import { redirect } from "next/navigation";
import { supabase } from "@/lib/supabase";

type Column = { source: string; confidence: number | string; transform?: string };

export async function approve(id: string, form: FormData) {
  const db = await supabase();
  const { data } = await db.from("uploads").select("mapping").eq("id", id).single();
  const proposed = (data?.mapping ?? { columns: {} }) as { columns: Record<string, Column>; sources: string[] };
  const columns: Record<string, Column> = {};
  for (const [target, value] of form.entries()) {
    if (!target.startsWith("t:") || !value) continue;
    const t = target.slice(2), source = String(value), was = proposed.columns[t];
    columns[t] = { source, confidence: was?.source === source ? was.confidence : "manual" };
  }
  if (columns.smart_194 && form.get("temp_unit") === "F") columns.smart_194.transform = "fahrenheit_to_celsius";
  if (columns.capacity_tb && form.get("capacity_unit") === "bytes") columns.capacity_tb.transform = "bytes_to_tb";
  const missing = ["drive_id", "date", "model"].filter((t) => !columns[t]);
  if (missing.length) redirect(`/upload/${id}?error=${encodeURIComponent(`Map these required fields: ${missing.join(", ")}`)}`);
  const mapping = { ...proposed, columns, date_format: String(form.get("date_format")) };
  const { error } = await db.from("uploads").update({ mapping, status: "approved" }).eq("id", id);
  redirect(error ? `/upload/${id}?error=${encodeURIComponent(error.message)}` : `/upload/${id}`);
}
