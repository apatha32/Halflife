"use client";

import { CartesianGrid, Legend, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

export type Point = { date: string } & Record<string, number | null | string>;

const SERIES = [
  ["smart_5", "Reallocated sectors", "var(--series-1)"],
  ["smart_197", "Pending sectors", "var(--series-2)"],
  ["smart_187", "Uncorrectable errors", "var(--series-3)"],
  ["smart_198", "Offline uncorrectable", "var(--series-4)"],
] as const;

function Panel({ data, series, scoreDate, risk, height }: {
  data: Point[]; series: readonly (readonly [string, string, string])[]; scoreDate?: string; risk?: string; height: number;
}) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <LineChart data={data} margin={{ top: 16, right: 16, bottom: 0, left: 0 }}>
        <CartesianGrid stroke="var(--grid)" vertical={false} />
        <XAxis dataKey="date" tick={{ fontSize: 11, fill: "var(--muted)" }} minTickGap={40} />
        <YAxis tick={{ fontSize: 11, fill: "var(--muted)" }} width={48} />
        <Tooltip contentStyle={{ background: "var(--surface)", border: "1px solid var(--grid)", fontSize: 12 }} />
        {series.length > 1 && <Legend wrapperStyle={{ fontSize: 12 }} />}
        {series.map(([key, name, color]) => (
          <Line key={key} dataKey={key} name={name} stroke={color} strokeWidth={2} dot={false} connectNulls isAnimationActive={false} />
        ))}
        {scoreDate && (
          <ReferenceLine x={scoreDate} stroke="var(--muted)" strokeDasharray="4 3"
            label={{ value: risk, position: "insideTopRight", fontSize: 11, fill: "var(--muted)" }} />
        )}
      </LineChart>
    </ResponsiveContainer>
  );
}

export default function Chart({ data, scoreDate, risk }: { data: Point[]; scoreDate: string; risk: string }) {
  return (
    <div className="space-y-6 rounded border border-stone-200 bg-[var(--surface)] p-3 dark:border-stone-700">
      <section aria-label="Error counters">
        <h2 className="px-1 text-sm font-medium">Error counters, last 180 days</h2>
        <Panel data={data} series={SERIES} scoreDate={scoreDate} risk={risk} height={260} />
      </section>
      <section aria-label="Temperature">
        <h2 className="px-1 text-sm font-medium">Temperature (°C)</h2>
        <Panel data={data} series={[["smart_194", "Temperature", "var(--series-1)"]]} scoreDate={scoreDate} height={140} />
      </section>
    </div>
  );
}
