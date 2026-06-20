/** Headline tiles: the only boxed elements on the page. Up to 3. Title, annual $, action, sparkline. */

import { AnalysisHeadline } from "../../types";
import { formatUSD } from "../../lib/format";

interface HeadlineBandProps {
  headlines: AnalysisHeadline[];
}

interface SparklineProps {
  series: { month: string; value: number }[];
}

function Sparkline({ series }: SparklineProps) {
  if (series.length < 2) return null;
  const vals = series.map((s) => s.value);
  const min = Math.min(...vals);
  const max = Math.max(...vals);
  const range = max - min || 1;
  const w = 80;
  const h = 28;
  const pts = vals
    .map((v, i) => {
      const x = (i / (vals.length - 1)) * w;
      const y = h - ((v - min) / range) * h;
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");

  return (
    <svg width={w} height={h} className="overflow-visible">
      <polyline
        points={pts}
        fill="none"
        stroke="#d97706"
        strokeWidth="1.5"
        strokeLinejoin="round"
        strokeLinecap="round"
        opacity="0.8"
      />
    </svg>
  );
}

function HeadlineTile({ h }: { h: AnalysisHeadline }) {
  return (
    <div className="flex flex-col gap-3 bg-slate-900 border border-slate-700 rounded-lg p-5">
      <div className="flex items-start justify-between gap-3">
        <span className="text-sm font-semibold text-slate-100 leading-snug">{h.title}</span>
        <span className="text-xs text-slate-500 uppercase tracking-wide shrink-0 pt-0.5">{h.category}</span>
      </div>
      <div className="flex items-end justify-between gap-4">
        <div className="flex flex-col gap-0.5">
          <span className="text-3xl font-bold tabular-nums text-amber-400 leading-none">
            {formatUSD(h.annual_impact)}
          </span>
          <span className="text-xs text-slate-500 uppercase tracking-wide">annual opportunity</span>
        </div>
        <Sparkline series={h.series ?? []} />
      </div>
      <p className="text-xs text-slate-300 leading-relaxed border-t border-slate-800 pt-3">{h.action}</p>
    </div>
  );
}

export function HeadlineBand({ headlines }: HeadlineBandProps) {
  const tiles = (headlines ?? []).slice(0, 3);
  if (tiles.length === 0) return null;

  return (
    <div className={`grid gap-4 ${tiles.length === 1 ? "grid-cols-1 max-w-sm" : tiles.length === 2 ? "grid-cols-1 sm:grid-cols-2" : "grid-cols-1 sm:grid-cols-2 lg:grid-cols-3"}`}>
      {tiles.map((h, i) => (
        <HeadlineTile key={`${h.title}-${i}`} h={h} />
      ))}
    </div>
  );
}
