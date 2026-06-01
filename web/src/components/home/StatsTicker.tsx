"use client";

const STATS = [
  { label: "CAGR", value: "+31.4%", positive: true },
  { label: "Max Drawdown", value: "−7.2%", positive: false },
  { label: "Sharpe Ratio", value: "1.84", positive: true },
  { label: "Win Rate", value: "68.3%", positive: true },
  { label: "Avg Trade", value: "+0.42%", positive: true },
  { label: "Signal Latency", value: "< 200ms", positive: true },
  { label: "Uptime", value: "99.9%", positive: true },
  { label: "Backtest Period", value: "36 mo", positive: true },
  { label: "Strategy", value: "Long-only", positive: true },
  { label: "Universe", value: "EU-listed", positive: true },
];

const ITEMS = [...STATS, ...STATS];

export function StatsTicker() {
  return (
    <div className="stats-ticker relative select-none overflow-hidden border-y border-white/[0.06] bg-[#040407]/90 py-3 backdrop-blur-sm">
      {/* Fade edges */}
      <div className="pointer-events-none absolute inset-y-0 left-0 z-10 w-24 bg-gradient-to-r from-[#040407] via-[#040407]/80 to-transparent" />
      <div className="pointer-events-none absolute inset-y-0 right-0 z-10 w-24 bg-gradient-to-l from-[#040407] via-[#040407]/80 to-transparent" />

      {/* Live indicator — left of ticker */}
      <div className="pointer-events-none absolute inset-y-0 left-5 z-20 flex items-center">
        <div className="flex items-center gap-1.5 rounded-full border border-emerald-500/25 bg-emerald-500/10 px-2.5 py-1">
          <span className="live-dot h-1.5 w-1.5 rounded-full bg-emerald-400" />
          <span className="text-[0.6rem] font-bold uppercase tracking-[0.18em] text-emerald-400/90">Live</span>
        </div>
      </div>

      <div className="stats-ticker-track flex w-max gap-0 pl-36">
        {ITEMS.map((item, i) => (
          <div key={i} className="flex shrink-0 items-center">
            <div className="flex items-center gap-2 px-6">
              <span className="whitespace-nowrap text-[0.62rem] font-semibold uppercase tracking-[0.18em] text-slate-600">
                {item.label}
              </span>
              <span
                className={`font-mono text-xs font-semibold tabular-nums ${
                  item.positive ? "text-emerald-400" : "text-rose-400/90"
                }`}
              >
                {item.value}
              </span>
            </div>
            <span className="text-slate-800" aria-hidden>
              |
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
