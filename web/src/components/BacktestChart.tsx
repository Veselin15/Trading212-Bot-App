"use client";

import {
  Area,
  AreaChart,
  ResponsiveContainer,
  Tooltip,
  type TooltipProps,
  XAxis,
  YAxis,
} from "recharts";
import type { NameType, ValueType } from "recharts/types/component/DefaultTooltipContent";

type BacktestPoint = {
  month: string; // e.g. "Apr 2023"
  value: number; // portfolio value
};

function formatUSD(value: number) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(value);
}

function generateMockBacktestData(): BacktestPoint[] {
  // IMPORTANT: This is mock data designed to look like real trading
  // without revealing any actual trade log.
  const start = 10_000;
  const months = 36;

  // Crafted monthly returns: mostly positive, with flats and minor drawdowns (2–4%).
  // The curve ends around ~$18.5k to reflect ~29% APY over ~3 years.
  const returns: number[] = [
    0.018, 0.012, -0.021, 0.024, 0.008, 0.0, 0.019, -0.015, 0.028, 0.011, 0.006, 0.021,
    0.014, -0.033, 0.026, 0.009, 0.0, 0.017, 0.022, -0.018, 0.025, 0.012, 0.007, 0.019,
    0.016, -0.027, 0.023, 0.01, 0.004, 0.018, 0.02, -0.014, 0.021, 0.013, 0.008, 0.017,
  ];

  const now = new Date();
  const baseYear = now.getFullYear();
  const baseMonth = now.getMonth(); // 0..11

  let v = start;
  const data: BacktestPoint[] = [];

  for (let i = months - 1; i >= 0; i -= 1) {
    const d = new Date(baseYear, baseMonth - i, 1);
    const label = d.toLocaleString("en-US", { month: "short", year: "numeric" });

    const r = returns[months - 1 - i] ?? 0.012;
    v = Math.max(0, v * (1 + r));

    // Round to whole dollars for a cleaner tooltip.
    data.push({ month: label, value: Math.round(v) });
  }

  return data;
}

function BacktestTooltip({ active, payload, label }: TooltipProps<ValueType, NameType>) {
  if (!active || !payload?.length) return null;
  const v = payload[0]?.value;
  if (typeof v !== "number") return null;

  return (
    <div className="rounded-2xl border border-slate-800/80 bg-slate-950/90 px-4 py-3 shadow-lg backdrop-blur">
      <div className="text-xs font-semibold uppercase tracking-wide text-slate-400">Month</div>
      <div className="mt-1 text-sm font-medium text-slate-50">{label}</div>
      <div className="mt-3 text-xs font-semibold uppercase tracking-wide text-slate-400">Portfolio Value</div>
      <div className="mt-1 text-sm font-medium text-emerald-300">{formatUSD(v)}</div>
    </div>
  );
}

export function BacktestChart({ className }: { className?: string }) {
  const data = generateMockBacktestData();

  return (
    <div className={className}>
      <div className="h-[260px] w-full">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data} margin={{ top: 10, right: 12, left: 0, bottom: 0 }}>
            <defs>
              <linearGradient id="equityFill" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#22c55e" stopOpacity={0.26} />
                <stop offset="55%" stopColor="#38bdf8" stopOpacity={0.12} />
                <stop offset="100%" stopColor="#020617" stopOpacity={0} />
              </linearGradient>
            </defs>

            {/* No prominent grid lines (premium / minimal) */}
            <XAxis
              dataKey="month"
              tick={false}
              axisLine={false}
              tickLine={false}
              minTickGap={40}
            />
            <YAxis
              width={0}
              tick={false}
              axisLine={false}
              tickLine={false}
              domain={["dataMin - 600", "dataMax + 600"]}
            />

            <Tooltip cursor={{ stroke: "rgba(148,163,184,0.25)", strokeWidth: 1 }} content={<BacktestTooltip />} />

            <Area
              type="monotone"
              dataKey="value"
              stroke="#34d399"
              strokeWidth={2.5}
              fill="url(#equityFill)"
              fillOpacity={1}
              dot={false}
              activeDot={{ r: 4, strokeWidth: 2, stroke: "#0f172a", fill: "#34d399" }}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

