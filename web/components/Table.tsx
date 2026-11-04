import type { ReactNode } from "react";

export type Column = { key: string; label: string; numeric?: boolean; wide?: boolean };

export default function Table({ columns, rows }: { columns: Column[]; rows: Record<string, ReactNode>[] }) {
  return (
    <div className="overflow-x-auto rounded border border-stone-200 dark:border-stone-700">
      <table className="w-full text-sm">
        <thead className="bg-stone-50 text-left text-stone-600 dark:bg-stone-800 dark:text-stone-300">
          <tr>
            {columns.map((c) => (
              <th key={c.key} className={`px-3 py-2 font-medium whitespace-nowrap ${c.numeric ? "text-right" : ""} ${c.wide ? "hidden sm:table-cell" : ""}`}>
                {c.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={i} className="border-t border-stone-200 dark:border-stone-700">
              {columns.map((c) => (
                <td key={c.key} className={`px-3 py-2 ${c.numeric ? "text-right tabular-nums" : ""} ${c.wide ? "hidden sm:table-cell" : ""}`}>
                  {r[c.key]}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
