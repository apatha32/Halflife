"use server";

import { headers } from "next/headers";
import { redirect } from "next/navigation";
import { supabase } from "@/lib/supabase";

export async function sendMagicLink(form: FormData) {
  const db = await supabase();
  const origin = (await headers()).get("origin");
  const { error } = await db.auth.signInWithOtp({
    email: String(form.get("email")),
    options: { emailRedirectTo: `${origin}/auth/callback`, shouldCreateUser: false },
  });
  redirect(error ? `/login?error=${encodeURIComponent(error.message)}` : "/login?sent=1");
}

export async function demoLogin(form: FormData) {
  const db = await supabase();
  const { error } = await db.auth.signInWithPassword({
    email: String(form.get("email")),
    password: process.env.DEMO_PASSWORD ?? "",
  });
  redirect(error ? `/login?error=${encodeURIComponent(error.message)}` : "/dashboard");
}

export async function signOut() {
  await (await supabase()).auth.signOut();
  redirect("/login");
}
