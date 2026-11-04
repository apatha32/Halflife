"use client";

import { CartesianGrid, Legend, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

export type Point = { date: string } & Record<string, number | null | string>;
type Series = readonly [key: string, name: string, color: string, dash?: string];

const COUNTERS: Series[] = [
  ["smart_5", "Reallocated sectors", "var(--series-1)"],
  ["smart_197", "Pending sectors", "var(--series-2)"],
  ["smart_187", "Uncorrectable errors", "var(--series-3)", "6 4"],
  ["smart_198", "Offline uncorrectable", "var(--series-4)", "2 3"],
];

function Panel({ data, series, scoreDate, risk, height }: {
  data: Point[]; series: Series[]; scoreDate?: string; risk?: string; height: number;
}) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <LineChart data={data} margin={{ top: 16, right: 16, bottom: 0, left: 0 }}>
        <CartesianGrid stroke="var(--grid)" vertical={false} />
        <XAxis dataKey="date" tick={{ fontSize: 11, fill: "var(--muted)" }} stroke="var(--grid)" minTickGap={40} />
        <YAxis tick={{ fontSize: 11, fill: "var(--muted)" }} stroke="var(--grid)" width={48} />
        <Tooltip
          contentStyle={{ background: "#000", border: "1px solid #39ff14", fontSize: 12 }}
          labelStyle={{ color: "#fff" }}
          cursor={{ stroke: "#39ff14", strokeOpacity: 0.4 }}
        />
        {series.length > 1 && <Legend wrapperStyle={{ fontSize: 12, color: "var(--muted)" }} />}
        {series.map(([key, name, color, dash]) => (
          <Line key={key} dataKey={key} name={name} stroke={color} strokeDasharray={dash} strokeWidth={2}
            dot={false} activeDot={{ r: 4, stroke: "#000", strokeWidth: 2 }} connectNulls animationDuration={1200} />
        ))}
        {scoreDate && (
          <ReferenceLine x={scoreDate} stroke="#39ff14" strokeDasharray="4 3"
            label={{ value: risk, position: "insideTopRight", fontSize: 11, fill: "#39ff14" }} />
        )}
      </LineChart>
    </ResponsiveContainer>
  );
}

export default function Chart({ data, scoreDate, risk }: { data: Point[]; scoreDate?: string; risk: string }) {
  return (
    <div className="space-y-6 border border-line bg-panel p-3">
      <section aria-label="Error counters">
        <h2 className="px-1 text-xs tracking-wider text-dim uppercase">Error counters, last 180 days</h2>
        <Panel data={data} series={COUNTERS} scoreDate={scoreDate} risk={risk} height={260} />
      </section>
      <section aria-label="Temperature">
        <h2 className="px-1 text-xs tracking-wider text-dim uppercase">Temperature (C)</h2>
        <Panel data={data} series={[["smart_194", "Temperature", "var(--series-2)"]]} scoreDate={scoreDate} height={140} />
      </section>
    </div>
  );
}
