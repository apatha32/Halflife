import { demoLogin, sendMagicLink } from "./actions";

const DEMOS = [
  ["demo@acme.test", "Acme Storage"],
  ["demo@northwind.test", "Northwind"],
];

export default async function Login({ searchParams }: { searchParams: Promise<{ sent?: string; error?: string }> }) {
  const { sent, error } = await searchParams;
  return (
    <div className="mx-auto max-w-sm space-y-8 py-8">
      <h1 className="text-2xl font-semibold">Sign in</h1>
      <form action={sendMagicLink} className="space-y-3">
        <label className="block text-sm font-medium" htmlFor="email">Email</label>
        <input id="email" name="email" type="email" required className="w-full rounded border border-stone-300 bg-transparent px-3 py-2" />
        <button className="w-full rounded bg-stone-900 px-3 py-2 text-white dark:bg-stone-100 dark:text-stone-900">Email me a magic link</button>
        {sent && <p className="text-sm text-stone-600 dark:text-stone-300">Check your email for a sign-in link.</p>}
        {error && <p className="text-sm text-red-700 dark:text-red-400">{error}</p>}
      </form>
      {process.env.DEMO_PASSWORD && (
        <div className="space-y-2">
          <p className="text-sm text-stone-600 dark:text-stone-300">Or try a demo fleet:</p>
          {DEMOS.map(([email, fleet]) => (
            <form key={email} action={demoLogin}>
              <input type="hidden" name="email" value={email} />
              <button className="w-full rounded border border-stone-300 px-3 py-2 dark:border-stone-600">Demo: {fleet}</button>
            </form>
          ))}
        </div>
      )}
    </div>
  );
}
