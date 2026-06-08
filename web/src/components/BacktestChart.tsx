"use client";

import { useInView, useReducedMotion } from "framer-motion";
import { useEffect, useMemo, useRef, useState } from "react";
import {
  Area,
  AreaChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { fetchStrategyDashboard } from "@/lib/strategy-dashboard";

type EquityPoint = {
  month: string;
  equity: number;
  ret_pct?: number;
  drawdown?: number;
  is_oos?: boolean;
};

type DashboardPayload = {
  generated_at?: string;
  hero?: {
    total_return_pct?: number;
    cagr_pct?: number;
    max_drawdown_pct?: number;
    oos_months?: number;
  };
  equity_5yr: EquityPoint[];
  // legacy fallback
  points?: EquityPoint[];
};

type ChartPoint = {
  month: string;
  value: number;
  is_oos?: boolean;
};

function formatUSD(value: number) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(value);
}

function monthLabel(yyyyMm: string) {
  const [y, m] = yyyyMm.split("-").map((x) => Number(x));
  if (!y || !m) return yyyyMm;
  const d = new Date(y, m - 1, 1);
  return d.toLocaleString("en-US", { month: "short", year: "numeric" });
}

function BacktestTooltip(props: unknown) {
  const { active, payload, label } = props as {
    active?: boolean;
    payload?: Array<{ value?: unknown; payload?: { is_oos?: boolean } }>;
    label?: string;
  };
  if (!active || !payload?.length) return null;
  const v = payload[0]?.value;
  if (typeof v !== "number") return null;
  const isOos = payload[0]?.payload?.is_oos;

  return (
    <div
      className="rounded-2xl border border-white/10 bg-[#0A0A0A] px-4 py-3 shadow-lg backdrop-blur transition-[transform,opacity] duration-150 ease-out"
      style={{ willChange: "transform" }}
    >
      <div className="text-xs font-semibold uppercase tracking-wide text-slate-400">Month</div>
      <div className="mt-1 flex items-center gap-2 text-sm font-medium text-slate-50">
        {label}
        {isOos && (
          <span className="rounded-full border border-emerald-500/30 bg-emerald-500/10 px-2 py-0.5 text-[0.6rem] font-semibold text-emerald-400">
            OOS
          </span>
        )}
      </div>
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
  const wrapRef = useRef<HTMLDivElement>(null);
  const inView = useInView(wrapRef, { once: true, amount: 0.22, margin: "0px 0px -10% 0px" });
  const reduceMotion = useReducedMotion();
  const [payload, setPayload] = useState<DashboardPayload | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    fetchStrategyDashboard<DashboardPayload>()
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

  // Prefer equity_5yr, fall back to legacy points field. Memoized so the derived
  // `data`/`oosStartMonth` don't recompute on every render from a fresh array ref.
  const rawPoints = useMemo<EquityPoint[]>(
    () => payload?.equity_5yr ?? payload?.points ?? [],
    [payload],
  );
  const oosStartMonth = rawPoints.find((p) => p.is_oos)?.month ?? null;

  const data = useMemo<ChartPoint[]>(() => {
    return rawPoints.map((p) => ({
      month: monthLabel(p.month),
      value: Math.round(startingBalance * p.equity),
      is_oos: p.is_oos,
    }));
  }, [rawPoints, startingBalance]);

  const allowDrawAnimation = Boolean(!reduceMotion && inView && data.length > 0);

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
        <div className="rounded-2xl border border-white/10 bg-[#0A0A0A] px-4 py-3 text-sm text-slate-300">
          Loading chart…
        </div>
      </div>
    );
  }

  // Find x-axis index for OOS reference line
  const oosLabelMonth = oosStartMonth ? monthLabel(oosStartMonth) : null;

  return (
    <div ref={wrapRef} className={className}>
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

            {oosLabelMonth && (
              <ReferenceLine
                x={oosLabelMonth}
                stroke="rgba(16,185,129,0.5)"
                strokeDasharray="4 3"
                strokeWidth={1.5}
                label={{
                  value: "OOS →",
                  position: "insideTopRight",
                  fontSize: 10,
                  fill: "#34d399",
                  fontWeight: 600,
                }}
              />
            )}

            <Tooltip
              animationDuration={160}
              animationEasing="ease-out"
              cursor={{ stroke: "rgba(148,163,184,0.35)", strokeWidth: 1 }}
              content={<BacktestTooltip />}
              allowEscapeViewBox={{ x: false, y: true }}
            />

            <Area
              type="monotone"
              dataKey="value"
              stroke="#34d399"
              strokeWidth={2.5}
              fill="url(#equityFill)"
              fillOpacity={1}
              dot={false}
              isAnimationActive={allowDrawAnimation}
              animationDuration={reduceMotion ? 0 : 1150}
              animationEasing="ease-out"
              activeDot={{ r: 4, strokeWidth: 2, stroke: "#0f172a", fill: "#34d399" }}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
