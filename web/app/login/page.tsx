import { demoLogin, sendMagicLink } from "./actions";

const DEMOS = [
  ["demo@acme.test", "Acme Storage"],
  ["demo@northwind.test", "Northwind"],
];

export default async function Login({ searchParams }: { searchParams: Promise<{ sent?: string; error?: string }> }) {
  const { sent, error } = await searchParams;
  return (
    <div className="mx-auto max-w-sm space-y-8 py-8">
      <div>
        <p className="text-xs tracking-widest text-neon uppercase">drive failure prediction</p>
        <h1 className="mt-2 text-3xl font-bold">Sign in</h1>
      </div>
      <form action={sendMagicLink} className="space-y-3">
        <label className="block text-xs tracking-wider text-dim uppercase" htmlFor="email">Email</label>
        <input id="email" name="email" type="email" required
          className="w-full border border-line bg-panel px-3 py-2 outline-none transition-shadow focus:border-neon focus:shadow-[0_0_10px_rgba(57,255,20,0.4)]" />
        <button className="neon-btn w-full border border-neon px-3 py-2 text-neon">Email me a magic link</button>
        {sent && <p className="text-sm text-neon">Check your email for a sign-in link.</p>}
        {error && <p className="text-sm text-paper">Error: {error}</p>}
      </form>
      {process.env.DEMO_PASSWORD && (
        <div className="space-y-2">
          <p className="text-xs tracking-wider text-dim uppercase">or open a demo fleet</p>
          {DEMOS.map(([email, fleet]) => (
            <form key={email} action={demoLogin}>
              <input type="hidden" name="email" value={email} />
              <button className="neon-btn w-full border border-line px-3 py-2 text-left">
                <span className="text-dim">demo /</span> {fleet}
              </button>
            </form>
          ))}
        </div>
      )}
    </div>
  );
}
