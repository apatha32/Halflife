import { createServerClient } from "@supabase/ssr";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";

export async function supabase() {
  const store = await cookies();
  return createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        getAll: () => store.getAll(),
        setAll: (all) => {
          try {
            all.forEach(({ name, value, options }) => store.set(name, value, options));
          } catch {
            // Server components cannot set cookies; proxy.ts refreshes the session instead.
          }
        },
      },
    },
  );
}

/** The signed-in user's client and first fleet; redirects to /login when signed out. */
export async function session() {
  const db = await supabase();
  const { data } = await db.auth.getUser();
  if (!data.user) redirect("/login");
  const { data: fleet } = await db.from("fleets").select("id, name").limit(1).single();
  return { db, user: data.user, fleet: fleet as { id: string; name: string } | null };
}
