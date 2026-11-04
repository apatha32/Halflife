import Link from "next/link";
import "./globals.css";
import { supabase } from "@/lib/supabase";
import { signOut } from "./login/actions";

export const metadata = { title: "Halflife", description: "Replace drives before they die without pulling healthy ones." };

export default async function RootLayout({ children }: { children: React.ReactNode }) {
  const { data } = await (await supabase()).auth.getUser();
  return (
    <html lang="en">
      <body className="flex min-h-screen flex-col bg-stone-50 text-stone-900 dark:bg-stone-900 dark:text-stone-100">
        <nav className="border-b border-stone-200 bg-white dark:border-stone-700 dark:bg-stone-950">
          <div className="mx-auto flex max-w-5xl flex-wrap items-center gap-x-5 gap-y-2 px-4 py-3 text-sm">
            <Link href="/pull-list" className="mr-auto text-base font-semibold">Halflife</Link>
            {data.user && (
              <>
                <Link href="/pull-list">Pull list</Link>
                <Link href="/data-quality">Data quality</Link>
                <form action={signOut}><button className="text-stone-500 dark:text-stone-400">Sign out</button></form>
              </>
            )}
          </div>
        </nav>
        <main className="mx-auto w-full max-w-5xl flex-1 px-4 py-6">{children}</main>
        <footer className="border-t border-stone-200 px-4 py-4 text-center text-xs text-stone-500 dark:border-stone-700 dark:text-stone-400">
          Data: <a className="underline" href="https://www.backblaze.com/cloud-storage/resources/hard-drive-test-data">Backblaze Drive Stats</a>, used under Backblaze&apos;s terms. Halflife is not affiliated with Backblaze.
        </footer>
      </body>
    </html>
  );
}
