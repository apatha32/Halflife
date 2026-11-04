import { JetBrains_Mono } from "next/font/google";
import Link from "next/link";
import "./globals.css";
import { supabase } from "@/lib/supabase";
import { signOut } from "./login/actions";

const mono = JetBrains_Mono({ subsets: ["latin"], variable: "--font-jetbrains" });

export const metadata = { title: "Halflife", description: "Replace drives before they die without pulling healthy ones." };

export default async function RootLayout({ children }: { children: React.ReactNode }) {
  const { data } = await (await supabase()).auth.getUser();
  return (
    <html lang="en" className={mono.variable}>
      <body className="flex min-h-screen flex-col font-mono text-paper">
        <nav className="scanbar border-b border-line bg-ink/90 backdrop-blur">
          <div className="mx-auto flex max-w-5xl flex-wrap items-center gap-x-5 gap-y-2 px-4 py-3 text-sm">
            <Link href="/pull-list" className="cursor mr-auto text-base font-bold tracking-widest uppercase">
              half<span className="text-neon">life</span>
            </Link>
            {data.user && (
              <>
                <Link className="text-dim transition-colors hover:text-neon" href="/pull-list">pull list</Link>
                <Link className="text-dim transition-colors hover:text-neon" href="/data-quality">data quality</Link>
                <form action={signOut}><button className="text-dim transition-colors hover:text-paper">sign out</button></form>
              </>
            )}
          </div>
        </nav>
        <main className="rise mx-auto w-full max-w-5xl flex-1 px-4 py-8">{children}</main>
        <footer className="border-t border-line px-4 py-4 text-center text-xs text-dim">
          Data: <a className="text-paper underline decoration-neon underline-offset-4" href="https://www.backblaze.com/cloud-storage/resources/hard-drive-test-data">Backblaze Drive Stats</a>, used under Backblaze&apos;s terms. Halflife is not affiliated with Backblaze.
        </footer>
      </body>
    </html>
  );
}
