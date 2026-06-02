"use client";

import { useInView, useReducedMotion } from "framer-motion";
import { useEffect, useMemo, useRef, useState } from "react";
import CountUp from "react-countup";

type HeroMetrics = {
  total_return_pct?: number;
  cagr_pct?: number;
  max_drawdown_pct?: number;
  win_rate_pct?: number;
  sharpe_ratio?: number;
  profit_factor?: number;
  total_trades?: number;
  oos_months?: number;
  avg_hold_h?: number;
};

type DashboardPayload = {
  generated_at?: string;
  hero?: HeroMetrics;
  equity_5yr?: Array<{ month: string; equity: number; is_oos?: boolean }>;
  // legacy fields
  summary?: {
    total_return_pct?: number;
    cagr_pct?: number;
    max_drawdown_pct?: number;
  };
  meta?: {
    start_utc?: string;
    end_utc?: string;
    symbols?: string[];
  };
};

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
  const [payload, setPayload] = useState<DashboardPayload | null>(null);
  const [error, setError] = useState<string | null>(null);
  const rootRef = useRef<HTMLDivElement>(null);
  const inView = useInView(rootRef, { once: true, amount: 0.05, margin: "0px 0px 80px 0px" });

  useEffect(() => {
    let cancelled = false;
    fetch("/strategy_dashboard.json", { cache: "no-store" })
      .then(async (r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return (await r.json()) as DashboardPayload;
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
    if (!payload) return null;

    // Prefer new hero metrics; fall back to legacy summary field
    const hero = payload.hero;
    const legacy = payload.summary;

    const totalReturnPct  = hero?.total_return_pct  ?? legacy?.total_return_pct;
    const cagrPct         = hero?.cagr_pct          ?? legacy?.cagr_pct;
    const maxDrawdownPct  = hero?.max_drawdown_pct   ?? legacy?.max_drawdown_pct;
    const winRatePct      = hero?.win_rate_pct;
    const sharpeRatio     = hero?.sharpe_ratio;
    const totalTrades     = hero?.total_trades;
    const oosMonths       = hero?.oos_months;

    if (totalReturnPct === undefined && cagrPct === undefined) return null;

    return {
      totalReturnPct,
      cagrPct,
      maxDrawdownPct,
      winRatePct,
      sharpeRatio,
      totalTrades,
      oosMonths,
      generatedAt: payload.generated_at,
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
      {/* Period / version info */}
      {(summary.oosMonths !== undefined || summary.generatedAt) && (
        <div className="rounded-2xl border border-white/10 bg-[#0A0A0A] px-4 py-3 transition-[border-color,box-shadow] duration-200 hover:border-emerald-500/25 hover:shadow-[0_0_24px_-10px_rgba(16,185,129,0.22)]">
          <div className="text-xs font-semibold uppercase tracking-wide text-slate-400">Period</div>
          <div className="mt-1 text-sm font-medium text-slate-50">
            5-year simulation · {summary.oosMonths ?? "?"} months out-of-sample
          </div>
          {summary.generatedAt && (
            <div className="mt-1 text-xs text-slate-500">
              SwingStrategyV3 · AI Ensemble v4 · updated {summary.generatedAt}
            </div>
          )}
        </div>
      )}

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
          <div className="mt-1 text-xs text-slate-400">Over the full simulation period</div>
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
          <div className="mt-1 text-xs text-slate-400">Annualised return / peak-to-trough</div>
        </div>
      </div>

      {/* Extra metrics row when available */}
      {(summary.winRatePct !== undefined || summary.sharpeRatio !== undefined || summary.totalTrades !== undefined) && (
        <div className="grid gap-3 sm:grid-cols-3">
          {typeof summary.winRatePct === "number" && (
            <div className="rounded-2xl border border-white/10 bg-[#0A0A0A] px-4 py-3 transition-[border-color,box-shadow] duration-200 hover:border-emerald-500/25 hover:shadow-[0_0_24px_-10px_rgba(16,185,129,0.22)]">
              <div className="text-xs font-semibold uppercase tracking-wide text-slate-400">Win rate</div>
              <div className="mt-1 text-xl font-semibold tracking-tight text-slate-50">
                <MetricCount end={summary.winRatePct} decimals={1} suffix="%" active={inView} />
              </div>
            </div>
          )}
          {typeof summary.sharpeRatio === "number" && (
            <div className="rounded-2xl border border-white/10 bg-[#0A0A0A] px-4 py-3 transition-[border-color,box-shadow] duration-200 hover:border-emerald-500/25 hover:shadow-[0_0_24px_-10px_rgba(16,185,129,0.22)]">
              <div className="text-xs font-semibold uppercase tracking-wide text-slate-400">Sharpe ratio</div>
              <div className="mt-1 text-xl font-semibold tracking-tight text-slate-50">
                <MetricCount end={summary.sharpeRatio} decimals={2} active={inView} />
              </div>
            </div>
          )}
          {typeof summary.totalTrades === "number" && (
            <div className="rounded-2xl border border-white/10 bg-[#0A0A0A] px-4 py-3 transition-[border-color,box-shadow] duration-200 hover:border-emerald-500/25 hover:shadow-[0_0_24px_-10px_rgba(16,185,129,0.22)]">
              <div className="text-xs font-semibold uppercase tracking-wide text-slate-400">Total trades</div>
              <div className="mt-1 text-xl font-semibold tracking-tight text-slate-50">
                <MetricCount end={summary.totalTrades} decimals={0} active={inView} />
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
