import { createBrowserClient } from "@supabase/ssr";

/** Supabase client in the browser, signed in with the user's session cookie (RLS applies). */
export const browserClient = () =>
  createBrowserClient(process.env.NEXT_PUBLIC_SUPABASE_URL!, process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!);
