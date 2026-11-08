import type { ReactNode } from "react";

export type Column = { key: string; label: string; numeric?: boolean; wide?: boolean };

export default function Table({ columns, rows }: { columns: Column[]; rows: Record<string, ReactNode>[] }) {
  const cls = (c: Column) => `${c.numeric ? "text-right font-mono tabular-nums" : ""} ${c.wide ? "hidden sm:table-cell" : ""}`;
  return (
    <div className="overflow-x-auto border border-line shade">
      <table className="w-full text-sm">
        <thead className="shade-head border-b border-line text-left font-mono text-xs tracking-wider text-dim uppercase">
          <tr>
            {columns.map((c) => (
              <th key={c.key} className={`px-3 py-2 font-medium whitespace-nowrap ${cls(c)}`}>{c.label}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr
              key={i}
              className="rise border-t border-line/60 hover:bg-neon-900/40 transition-colors hover:bg-neon-900/40"
              style={i < 12 ? { animationDelay: `${i * 20}ms` } : { animation: "none" }}
            >
              {columns.map((c) => (
                <td key={c.key} className={`px-3 py-2 ${cls(c)}`}>{r[c.key]}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
