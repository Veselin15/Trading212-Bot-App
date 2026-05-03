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
    <div className="relative select-none overflow-hidden border-y border-white/10 bg-zinc-900 py-3">
      <div className="pointer-events-none absolute inset-y-0 left-0 z-10 w-16 bg-gradient-to-r from-background to-transparent" />
      <div className="pointer-events-none absolute inset-y-0 right-0 z-10 w-16 bg-gradient-to-l from-background to-transparent" />

      <div
        className="flex w-max gap-10"
        style={{
          animation: "ticker-scroll 38s linear infinite",
        }}
      >
        {ITEMS.map((item, i) => (
          <div key={i} className="flex shrink-0 items-center gap-2">
            <span className="whitespace-nowrap text-xs uppercase tracking-wider text-slate-500">{item.label}</span>
            <span className={`font-mono text-sm ${item.positive ? "text-violet-400" : "text-red-400"}`}>
              {item.value}
            </span>
            <span className="text-xs text-slate-700">·</span>
          </div>
        ))}
      </div>

      <style>{`
        @keyframes ticker-scroll {
          from { transform: translateX(0); }
          to   { transform: translateX(-50%); }
        }
      `}</style>
    </div>
  );
}

