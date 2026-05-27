"use client";

const STATS = [
  { label: "CAGR", value: "+31.4%", positive: true },
  { label: "Max Drawdown", value: "-7.2%", positive: false },
  { label: "Sharpe Ratio", value: "1.84", positive: true },
  { label: "Win Rate", value: "68.3%", positive: true },
  { label: "Avg Trade", value: "+0.42%", positive: true },
  { label: "Signal Latency", value: "<200ms", positive: true },
  { label: "Uptime", value: "99.9%", positive: true },
  { label: "Backtest Period", value: "36 mo", positive: true },
];

const ITEMS = [...STATS, ...STATS];

export function StatsTicker() {
  return (
    <div className="stats-ticker relative select-none overflow-hidden border-y border-white/[0.06] bg-[#060608]/90 py-3.5 backdrop-blur-sm">
      <div className="pointer-events-none absolute inset-y-0 left-0 z-10 w-20 bg-gradient-to-r from-background via-background/80 to-transparent" />
      <div className="pointer-events-none absolute inset-y-0 right-0 z-10 w-20 bg-gradient-to-l from-background via-background/80 to-transparent" />

      <div className="stats-ticker-track flex w-max gap-12">
        {ITEMS.map((item, i) => (
          <div key={i} className="flex shrink-0 items-center gap-2.5">
            <span className="whitespace-nowrap text-[0.65rem] font-semibold uppercase tracking-[0.18em] text-slate-500">
              {item.label}
            </span>
            <span
              className={`font-mono text-sm font-medium tabular-nums ${item.positive ? "text-emerald-400" : "text-rose-400/90"}`}
            >
              {item.value}
            </span>
            <span className="text-slate-700" aria-hidden>
              ·
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
