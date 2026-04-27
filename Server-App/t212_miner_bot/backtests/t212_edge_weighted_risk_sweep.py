"""
Parameter sweep for Edge-Weighted Risk (EWR) portfolio allocation.
"""

from __future__ import annotations

import argparse
import itertools
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from t212_miner_bot.backtests.t212_edge_weighted_risk_backtest import run as run_ewr


def main() -> None:
    parser = argparse.ArgumentParser(description="Sweep EWR allocation parameters on 2-year data.")
    parser.add_argument("--days", type=int, default=730)
    parser.add_argument("--slippage-bps", type=float, default=5.0)
    args = parser.parse_args()

    # Reduced but still meaningful search space for practical runtime.
    lookbacks = [2, 3, 4]
    z_alphas = [0.15, 0.20, 0.25]
    min_mults = [0.6]
    max_mults = [1.3, 1.4]
    min_samples_set = [2]

    rows: list[dict[str, float]] = []
    total = 0
    for lookback, z_alpha, min_mult, max_mult, min_samples in itertools.product(
        lookbacks, z_alphas, min_mults, max_mults, min_samples_set
    ):
        if min_mult >= 1.0 or max_mult <= 1.0 or min_mult >= max_mult:
            continue
        total += 1
        res = run_ewr(
            days=max(args.days, 120),
            slippage_bps=max(args.slippage_bps, 0.0),
            lookback_months=lookback,
            z_alpha=z_alpha,
            min_mult=min_mult,
            max_mult=max_mult,
            min_samples=min_samples,
            verbose=False,
        )
        rows.append(
            {
                "lookback": float(lookback),
                "z_alpha": z_alpha,
                "min_mult": min_mult,
                "max_mult": max_mult,
                "min_samples": float(min_samples),
                "baseline_total": float(res["baseline_total"]),
                "ewr_total": float(res["ewr_total"]),
                "delta_pp": float(res["delta_pp"]),
            }
        )
        print(f"[RUN] {total} candidates complete", flush=True)

    ranked = sorted(rows, key=lambda r: r["delta_pp"], reverse=True)
    print("\nTop 15 EWR parameter sets:")
    print("-" * 110)
    print(
        f"{'Rank':<5} {'Delta pp':>9} {'EWR%':>9} {'Base%':>9} {'Lookback':>9} "
        f"{'z_alpha':>8} {'min_mult':>9} {'max_mult':>9} {'min_samples':>12}"
    )
    print("-" * 110)
    for i, r in enumerate(ranked[:15], start=1):
        print(
            f"{i:<5} {r['delta_pp']:>9.2f} {r['ewr_total']:>9.2f} {r['baseline_total']:>9.2f} "
            f"{int(r['lookback']):>9d} {r['z_alpha']:>8.2f} {r['min_mult']:>9.2f} "
            f"{r['max_mult']:>9.2f} {int(r['min_samples']):>12d}"
        )
    print("-" * 110)
    if ranked:
        best = ranked[0]
        print(
            f"[RESULT] Best delta={best['delta_pp']:.2f} pp | lookback={int(best['lookback'])} "
            f"z_alpha={best['z_alpha']:.2f} min_mult={best['min_mult']:.2f} "
            f"max_mult={best['max_mult']:.2f} min_samples={int(best['min_samples'])}"
        )


if __name__ == "__main__":
    main()
