"use client";

import { useEffect, useMemo, useState } from "react";

type EquityPoint = {
  month: string; // e.g. "2024-01"
  equity: number; // equity multiple (1.0 = starting capital)
};

type BacktestPayload = {
  meta?: {
    days?: number;
    symbols?: string[];
  };
  points: EquityPoint[];
};

function formatPct(value: number) {
  return new Intl.NumberFormat("en-US", {
    style: "percent",
    maximumFractionDigits: 0,
  }).format(value);
}

function monthToLabel(yyyyMm: string) {
  const [y, m] = yyyyMm.split("-").map((x) => Number(x));
  if (!y || !m) return yyyyMm;
  const d = new Date(y, m - 1, 1);
  return d.toLocaleString("en-US", { month: "short", year: "numeric" });
}

function computeMaxDrawdown(equity: number[]) {
  let peak = -Infinity;
  let maxDd = 0;
  for (const v of equity) {
    peak = Math.max(peak, v);
    if (peak > 0) maxDd = Math.min(maxDd, (v - peak) / peak);
  }
  return maxDd; // negative number, e.g. -0.12
}

export function BacktestSummary() {
  const [payload, setPayload] = useState<BacktestPayload | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    fetch("/backtest_equity.json", { cache: "no-store" })
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

    const points = payload.points;
    const start = points[0]!;
    const end = points[points.length - 1]!;

    const startEquity = Math.max(1e-9, start.equity);
    const endEquity = Math.max(1e-9, end.equity);

    const totalReturn = endEquity / startEquity - 1;
    const days = payload.meta?.days;
    const years = typeof days === "number" && days > 0 ? days / 365 : null;
    const cagr = years ? Math.pow(endEquity / startEquity, 1 / years) - 1 : null;

    const maxDrawdown = computeMaxDrawdown(points.map((p) => p.equity));

    return {
      startLabel: monthToLabel(start.month),
      endLabel: monthToLabel(end.month),
      symbols: payload.meta?.symbols ?? [],
      totalReturn,
      cagr,
      maxDrawdown,
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
          {summary.startLabel} → {summary.endLabel}
        </div>
        {summary.symbols.length ? (
          <div className="mt-1 text-xs text-slate-400">Universe: {summary.symbols.join(", ")}</div>
        ) : null}
      </div>

      <div className="rounded-2xl border border-slate-800/70 bg-slate-950/40 px-4 py-3">
        <div className="text-xs font-semibold uppercase tracking-wide text-slate-400">Total return (simulated)</div>
        <div className="mt-1 text-2xl font-semibold tracking-tight text-emerald-300">
          {formatPct(summary.totalReturn)}
        </div>
        <div className="mt-1 text-xs text-slate-400">From monthly equity multiples</div>
      </div>

      <div className="rounded-2xl border border-slate-800/70 bg-slate-950/40 px-4 py-3">
        <div className="text-xs font-semibold uppercase tracking-wide text-slate-400">CAGR / max drawdown</div>
        <div className="mt-1 text-sm font-medium text-slate-50">
          {summary.cagr == null ? "—" : formatPct(summary.cagr)} / {formatPct(Math.abs(summary.maxDrawdown))}
        </div>
        <div className="mt-1 text-xs text-slate-400">Max DD is approximate (monthly)</div>
      </div>
    </div>
  );
}

