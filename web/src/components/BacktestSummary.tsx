"use client";

import { useInView, useReducedMotion } from "framer-motion";
import { useEffect, useMemo, useRef, useState } from "react";
import CountUp from "react-countup";

type EquityPoint = {
  month: string;
  equity: number;
};

type BacktestPayload = {
  meta?: {
    start_utc?: string;
    end_utc?: string;
    symbols?: string[];
  };
  summary?: {
    total_return_pct?: number;
    cagr_pct?: number;
    max_drawdown_pct?: number;
  };
  points: EquityPoint[];
};

function formatDateRange(startUtc?: string, endUtc?: string) {
  if (!startUtc || !endUtc) return null;
  const start = new Date(startUtc);
  const end = new Date(endUtc);
  if (Number.isNaN(start.getTime()) || Number.isNaN(end.getTime())) return null;
  return `${start.toLocaleDateString("en-US", { year: "numeric", month: "short" })} → ${end.toLocaleDateString("en-US", { year: "numeric", month: "short" })}`;
}

function MetricCount({
  end,
  decimals,
  suffix = "",
  prefix = "",
  active,
}: {
  end: number;
  decimals: number;
  suffix?: string;
  prefix?: string;
  active: boolean;
}) {
  const reduce = useReducedMotion();
  const staticText = (
    <span className="tabular-nums">
      {prefix}
      {end.toFixed(decimals)}
      {suffix}
    </span>
  );
  if (reduce || !active) return staticText;
  return (
    <CountUp
      className="tabular-nums"
      duration={1.05}
      start={0}
      end={end}
      decimals={decimals}
      prefix={prefix}
      suffix={suffix}
      preserveValue
      useEasing
    />
  );
}

export function BacktestSummary() {
  const [payload, setPayload] = useState<BacktestPayload | null>(null);
  const [error, setError] = useState<string | null>(null);
  const rootRef = useRef<HTMLDivElement>(null);
  const inView = useInView(rootRef, { once: true, amount: 0.05, margin: "0px 0px 80px 0px" });

  useEffect(() => {
    let cancelled = false;
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

  const summary = useMemo(() => {
    if (!payload?.points?.length) return null;

    const totalReturnPct = payload.summary?.total_return_pct;
    const cagrPct = payload.summary?.cagr_pct;
    const maxDrawdownPct = payload.summary?.max_drawdown_pct;

    return {
      dateRange: formatDateRange(payload.meta?.start_utc, payload.meta?.end_utc),
      symbols: payload.meta?.symbols ?? [],
      totalReturnPct,
      cagrPct,
      maxDrawdownPct,
    };
  }, [payload]);

  if (error) {
    return (
      <div className="rounded-2xl border border-rose-500/25 bg-rose-500/10 px-4 py-3 text-sm text-rose-100">
        <div className="font-medium">Could not load results.</div>
        <div className="mt-1 font-mono text-xs text-rose-200/90">{error}</div>
      </div>
    );
  }

  if (!summary) {
    return (
      <div className="rounded-2xl border border-white/10 bg-[#0A0A0A] px-4 py-3 text-sm text-slate-300">
        Loading…
      </div>
    );
  }

  return (
    <div ref={rootRef} className="mt-4 flex flex-col gap-3 sm:mt-5">
      <div className="rounded-2xl border border-white/10 bg-[#0A0A0A] px-4 py-3 transition-[border-color,box-shadow] duration-200 hover:border-emerald-500/25 hover:shadow-[0_0_24px_-10px_rgba(16,185,129,0.22)]">
        <div className="text-xs font-semibold uppercase tracking-wide text-slate-400">Period</div>
        <div className="mt-1 text-sm font-medium text-slate-50">{summary.dateRange ?? "—"}</div>
        {summary.symbols.length ? (
          <div className="mt-1 text-xs text-slate-400">Universe: {summary.symbols.join(", ")}</div>
        ) : null}
      </div>

      <div className="grid gap-3 sm:grid-cols-2">
        <div className="rounded-2xl border border-white/10 bg-[#0A0A0A] px-4 py-3 transition-[border-color,box-shadow] duration-200 hover:border-emerald-500/25 hover:shadow-[0_0_24px_-10px_rgba(16,185,129,0.22)]">
          <div className="text-xs font-semibold uppercase tracking-wide text-slate-400">Total return</div>
          <div className="mt-1 text-2xl font-semibold tracking-tight text-emerald-300">
            {typeof summary.totalReturnPct === "number" ? (
              <MetricCount end={summary.totalReturnPct} decimals={1} suffix="%" active={inView} />
            ) : (
              "—"
            )}
          </div>
          <div className="mt-1 text-xs text-slate-400">Over the period above (model)</div>
        </div>

        <div className="rounded-2xl border border-white/10 bg-[#0A0A0A] px-4 py-3 transition-[border-color,box-shadow] duration-200 hover:border-emerald-500/25 hover:shadow-[0_0_24px_-10px_rgba(16,185,129,0.22)]">
          <div className="text-xs font-semibold uppercase tracking-wide text-slate-400">CAGR / max drawdown</div>
          <div className="mt-1 text-sm font-medium text-slate-50">
            {typeof summary.cagrPct === "number" && typeof summary.maxDrawdownPct === "number" ? (
              <>
                <MetricCount end={summary.cagrPct} decimals={1} suffix="%" active={inView} /> /{" "}
                <MetricCount end={Math.abs(summary.maxDrawdownPct)} decimals={1} suffix="%" active={inView} />
              </>
            ) : (
              "— / —"
            )}
          </div>
          <div className="mt-1 text-xs text-slate-400">For the same historical window</div>
        </div>
      </div>
    </div>
  );
}
