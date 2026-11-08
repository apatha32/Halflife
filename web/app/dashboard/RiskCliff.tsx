"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { pct } from "@/lib/format";

type Bar = { drive_id: string; rank: number; risk: number };

const W = 960, H = 280, L = 52, B = 30, T = 14;

export default function RiskCliff({ bars, k, pulled, rest }: { bars: Bar[]; k: number; pulled: number; rest: number }) {
  const router = useRouter();
  const [hover, setHover] = useState<Bar | null>(null);
  const top = Math.max(0.05, Math.ceil((bars[0]?.risk ?? 0.05) * 20) / 20);
  const bw = (W - L) / bars.length;
  const y = (r: number) => H - B - (r / top) * (H - B - T);
  const ticks = [0, top / 2, top];
  const kx = L + k * bw;
  return (
    <figure className="shade relative border border-line p-4">
      <figcaption className="mb-3 flex flex-wrap items-baseline justify-between gap-2">
        <span className="font-mono text-xs tracking-wider text-dim uppercase">Risk cliff: top {bars.length} drives by 30-day risk</span>
        <span className="font-mono text-xs text-soft">
          {hover ? `#${hover.rank} ${hover.drive_id} / ${pct(hover.risk)}` : "Hover a bar for the drive, click to open it"}
        </span>
      </figcaption>
      <div className="-mx-1 overflow-x-auto px-1">
      <svg viewBox={`0 0 ${W} ${H}`} className="block h-auto w-full min-w-[720px]" role="img"
        aria-label={`Sorted 30-day risk of the ${bars.length} riskiest drives. The first ${k}, this week's pull list, hold ${pulled.toFixed(1)} expected failures; the next ${bars.length - k} hold ${rest.toFixed(1)}.`}>
        <defs>
          <linearGradient id="pull" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#6dff4a" /><stop offset="1" stopColor="#1b9108" /></linearGradient>
          <linearGradient id="tail" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#5c5c5c" /><stop offset="1" stopColor="#262626" /></linearGradient>
        </defs>
        {ticks.map((t) => (
          <g key={t}>
            <line x1={L} x2={W} y1={y(t)} y2={y(t)} stroke="#1f1f1f" />
            <text x={L - 8} y={y(t) + 4} textAnchor="end" fontSize="14" fill="#8f8f8f" fontFamily="var(--font-mono)">{Math.round(t * 100)}%</text>
          </g>
        ))}
        {bars.map((b, i) => (
          <rect key={b.drive_id} className="cliff-bar" style={{ animationDelay: `${Math.min(i, 120) * 4}ms` }}
            x={L + i * bw + bw * 0.1} width={Math.max(bw * 0.8, 0.6)} y={y(b.risk)} height={Math.max(H - B - y(b.risk), 1)} rx={Math.min(bw * 0.4, 2)}
            fill={i < k ? "url(#pull)" : "url(#tail)"} opacity={hover && hover.drive_id !== b.drive_id ? 0.55 : 1}
            onMouseEnter={() => setHover(b)} onMouseLeave={() => setHover(null)}
            onClick={() => router.push(`/drives/${encodeURIComponent(b.drive_id)}`)} cursor="pointer" />
        ))}
        <line x1={kx} x2={kx} y1={T} y2={H - B} stroke="#39ff14" strokeDasharray="4 4" />
        <text x={kx + 8} y={T + 14} fontSize="15" fill="#39ff14" fontFamily="var(--font-mono)">this week&apos;s pull list: {k} drives, {pulled.toFixed(1)} expected failures</text>
        <text x={kx + 8} y={T + 36} fontSize="15" fill="#8f8f8f" fontFamily="var(--font-mono)">next {bars.length - k}: {rest.toFixed(1)} expected failures</text>
        <text x={L} y={H - 8} fontSize="14" fill="#8f8f8f" fontFamily="var(--font-mono)">rank 1</text>
        <text x={W} y={H - 8} textAnchor="end" fontSize="14" fill="#8f8f8f" fontFamily="var(--font-mono)">rank {bars.length}</text>
      </svg>
      </div>
    </figure>
  );
}
