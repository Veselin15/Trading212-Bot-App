"use client";

import { useEffect, useMemo, useState } from "react";

type EquityPoint = {
  month: string; // e.g. "2024-01"
  equity: number; // equity multiple (1.0 = starting capital)
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

function formatPct(value: number) {
  return new Intl.NumberFormat("en-US", {
    style: "percent",
    maximumFractionDigits: 0,
  }).format(value);
}

function formatDateRange(startUtc?: string, endUtc?: string) {
  if (!startUtc || !endUtc) return null;
  const start = new Date(startUtc);
  const end = new Date(endUtc);
  if (Number.isNaN(start.getTime()) || Number.isNaN(end.getTime())) return null;
  return `${start.toLocaleDateString("en-US", { year: "numeric", month: "short" })} → ${end.toLocaleDateString("en-US", { year: "numeric", month: "short" })}`;
}

export function BacktestSummary() {
  const [payload, setPayload] = useState<BacktestPayload | null>(null);
  const [error, setError] = useState<string | null>(null);

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
        <div className="font-medium">Failed to load backtest summary.</div>
        <div className="mt-1 font-mono text-xs text-rose-200/90">{error}</div>
      </div>
    );
  }

  if (!summary) {
    return (
      <div className="rounded-2xl border border-slate-800/70 bg-slate-950/40 px-4 py-3 text-sm text-slate-300">
        Loading summary…
      </div>
    );
  }

  return (
    <div className="grid gap-3 sm:grid-cols-3">
      <div className="rounded-2xl border border-slate-800/70 bg-slate-950/40 px-4 py-3">
        <div className="text-xs font-semibold uppercase tracking-wide text-slate-400">Backtest window</div>
        <div className="mt-1 text-sm font-medium text-slate-50">
          {summary.dateRange ?? "—"}
        </div>
        {summary.symbols.length ? (
          <div className="mt-1 text-xs text-slate-400">Universe: {summary.symbols.join(", ")}</div>
        ) : null}
      </div>

      <div className="rounded-2xl border border-slate-800/70 bg-slate-950/40 px-4 py-3">
        <div className="text-xs font-semibold uppercase tracking-wide text-slate-400">Total return (simulated)</div>
        <div className="mt-1 text-2xl font-semibold tracking-tight text-emerald-300">
          {typeof summary.totalReturnPct === "number" ? formatPct(summary.totalReturnPct / 100) : "—"}
        </div>
        <div className="mt-1 text-xs text-slate-400">From the strategy report snapshot</div>
      </div>

      <div className="rounded-2xl border border-slate-800/70 bg-slate-950/40 px-4 py-3">
        <div className="text-xs font-semibold uppercase tracking-wide text-slate-400">CAGR / max drawdown</div>
        <div className="mt-1 text-sm font-medium text-slate-50">
          {typeof summary.cagrPct === "number" ? formatPct(summary.cagrPct / 100) : "—"} /{" "}
          {typeof summary.maxDrawdownPct === "number" ? formatPct(Math.abs(summary.maxDrawdownPct) / 100) : "—"}
        </div>
        <div className="mt-1 text-xs text-slate-400">Backtest metrics are simulated</div>
      </div>
    </div>
  );
}

