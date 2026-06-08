// Shared loader for the static strategy backtest payload (`public/strategy_dashboard.json`).
//
// The home page renders <BacktestChart /> and <BacktestSummary /> together; without a
// shared cache each would fetch the same ~43 KB file independently. The file is a static
// asset that only changes on deploy, so we memoize a single in-flight/resolved promise and
// let the browser HTTP cache do the rest (no `cache: "no-store"`).

let inflight: Promise<unknown> | null = null;

export function fetchStrategyDashboard<T = unknown>(): Promise<T> {
  if (!inflight) {
    inflight = fetch("/strategy_dashboard.json")
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .catch((err) => {
        // Allow a later mount to retry instead of caching the rejection forever.
        inflight = null;
        throw err;
      });
  }
  return inflight as Promise<T>;
}
