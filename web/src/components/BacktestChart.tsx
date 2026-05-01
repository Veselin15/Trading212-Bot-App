"use client";

import { useEffect, useMemo, useState } from "react";
import {
  Area,
  AreaChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

type EquityPoint = {
  month: string; // e.g. "2024-01"
  equity: number; // equity multiple (1.0 = starting capital)
  ret_pct?: number;
  exposure?: number;
  breadth?: number;
};

type BacktestPayload = {
  meta?: {
    start_utc?: string;
    end_utc?: string;
    symbols?: string[];
    slippage_bps?: number;
  };
  summary?: {
    total_return_pct?: number;
    cagr_pct?: number;
    max_drawdown_pct?: number;
  };
  points: EquityPoint[];
};

type ChartPoint = {
  month: string;
  value: number; // portfolio value in USD
};

function formatUSD(value: number) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(value);
}

function monthLabel(yyyyMm: string) {
  // Expected input: YYYY-MM
  const [y, m] = yyyyMm.split("-").map((x) => Number(x));
  if (!y || !m) return yyyyMm;
  const d = new Date(y, m - 1, 1);
  return d.toLocaleString("en-US", { month: "short", year: "numeric" });
}

function BacktestTooltip(props: unknown) {
  const { active, payload, label } = props as {
    active?: boolean;
    payload?: Array<{ value?: unknown }>;
    label?: string;
  };
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

export function BacktestChart({
  className,
  startingBalance = 10_000,
}: {
  className?: string;
  startingBalance?: number;
}) {
  const [payload, setPayload] = useState<BacktestPayload | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    // IMPORTANT: This uses an aggregated monthly equity curve (no trade log exposed).
    fetch("/backtest_report.json", { cache: "no-store" })
      .then(async (r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return (await r.json()) as BacktestPayload;
      })
      .then((p) => {
        if (!cancelled) setPayload(p);
      })
      .catch((e: unknown) => {
        if (!cancelled) setError(e instanceof Error ? e.message : String(e));
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const data = useMemo<ChartPoint[]>(() => {
    const points = payload?.points ?? [];
    return points.map((p) => ({
      month: monthLabel(p.month),
      value: Math.round(startingBalance * p.equity),
    }));
  }, [payload, startingBalance]);

  if (error) {
    return (
      <div className={className}>
        <div className="rounded-2xl border border-rose-500/25 bg-rose-500/10 px-4 py-3 text-sm text-rose-100">
          <div className="font-medium">Could not load chart data.</div>
          <div className="mt-1 font-mono text-xs text-rose-200/90">{error}</div>
        </div>
      </div>
    );
  }

  if (!payload) {
    return (
      <div className={className}>
        <div className="rounded-2xl border border-slate-800/70 bg-slate-950/40 px-4 py-3 text-sm text-slate-300">
          Loading chart…
        </div>
      </div>
    );
  }

  return (
    <div className={className}>
      <div className="h-[260px] w-full">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data} margin={{ top: 10, right: 12, left: 0, bottom: 0 }}>
            <defs>
              <linearGradient id="equityFill" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#22c55e" stopOpacity={0.22} />
                <stop offset="55%" stopColor="#38bdf8" stopOpacity={0.1} />
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

