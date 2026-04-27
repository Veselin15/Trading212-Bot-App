"""
Export full Trading 212 Invest account history to files (JSON + CSV).

Uses the same credentials as the bot (T212_API_KEY, T212_SECRET_KEY, T212_BASE_URL
from .env — practice uses https://demo.trading212.com, live uses https://live.trading212.com).

Run from repo root:
  python -m t212_miner_bot.export_portfolio_history
  python -m t212_miner_bot.export_portfolio_history --out exports/t212_history

Official API docs (pagination, CSV export workflow):
  https://docs.trading212.com/api/historical-events

In-app alternative: Menu → History → Export → choose range and data types → download CSV.
"""
from __future__ import annotations

import argparse
import asyncio
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from t212_miner_bot.api_client import AsyncT212Client
from t212_miner_bot.config import T212_BASE_URL


def _flatten_row(r: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for k, v in r.items():
        if isinstance(v, (dict, list)):
            out[k] = json.dumps(v, ensure_ascii=False)
        else:
            out[k] = v
    return out


def _write_csv(rows: list[dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    flat = [_flatten_row(r) for r in rows]
    keys = sorted({k for row in flat for k in row.keys()})
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=keys, extrasaction="ignore")
        w.writeheader()
        for row in flat:
            w.writerow(row)


def _write_json(rows: list[dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")


async def _run(out_dir: Path, page_delay: float) -> None:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%SZ")
    base = out_dir / f"t212_export_{stamp}"
    base.mkdir(parents=True, exist_ok=True)

    async with AsyncT212Client() as client:
        print(f"Base URL: {T212_BASE_URL}")
        print("Fetching history orders (paginated, may take several minutes)...")
        orders = await client.fetch_history_orders(page_delay_sec=page_delay)
        print(f"  orders: {len(orders)} rows")
        print("Fetching cash transactions...")
        tx = await client.fetch_history_transactions(page_delay_sec=page_delay)
        print(f"  transactions: {len(tx)} rows")
        print("Fetching dividends...")
        divs = await client.fetch_history_dividends(page_delay_sec=page_delay)
        print(f"  dividends: {len(divs)} rows")

    _write_json(orders, base / "history_orders.json")
    _write_csv(orders, base / "history_orders.csv")
    _write_json(tx, base / "history_transactions.json")
    _write_csv(tx, base / "history_transactions.csv")
    _write_json(divs, base / "history_dividends.json")
    _write_csv(divs, base / "history_dividends.csv")

    meta = {
        "exported_at_utc": stamp,
        "base_url": T212_BASE_URL,
        "counts": {"orders": len(orders), "transactions": len(tx), "dividends": len(divs)},
        "note": "For broker-generated CSV bundles, use POST /api/v0/equity/history/exports (async).",
    }
    (base / "export_meta.json").write_text(
        json.dumps(meta, indent=2), encoding="utf-8"
    )
    print(f"\nWrote: {base.resolve()}")


def main() -> None:
    p = argparse.ArgumentParser(description="Export T212 full history to JSON/CSV.")
    p.add_argument(
        "--out",
        type=Path,
        default=Path("exports"),
        help="Output directory (creates t212_export_<timestamp> inside).",
    )
    p.add_argument(
        "--page-delay",
        type=float,
        default=10.5,
        help="Seconds between paginated history requests (T212 ~6/min limit). Default 10.5.",
    )
    args = p.parse_args()
    try:
        asyncio.run(_run(args.out, args.page_delay))
    except EnvironmentError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
