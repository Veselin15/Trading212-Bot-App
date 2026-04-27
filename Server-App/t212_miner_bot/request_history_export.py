"""
Request a broker-generated Trading 212 history CSV export (async workflow),
poll until finished, then download the CSV file.

Practice (demo): uses T212_BASE_URL=https://demo.trading212.com
Live:            uses T212_BASE_URL=https://live.trading212.com

Run:
  python -m t212_miner_bot.request_history_export --from 2024-01-01 --to 2026-04-01

Docs:
  https://docs.trading212.com/api/historical-events/requestreport.md
  https://docs.trading212.com/api/historical-events/getreports.md
"""

from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timezone
from pathlib import Path

import aiohttp

from t212_miner_bot.api_client import AsyncT212Client
from t212_miner_bot.config import T212_BASE_URL


def _utc_now_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%SZ")


async def _download(url: str, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=120)) as s:
        async with s.get(url) as resp:
            resp.raise_for_status()
            out_path.write_bytes(await resp.read())


async def run(
    *,
    time_from: str,
    time_to: str,
    out_dir: Path,
    poll_every_sec: float,
    include_orders: bool,
    include_transactions: bool,
    include_dividends: bool,
    include_interest: bool,
) -> Path:
    stamp = _utc_now_stamp()
    out_dir.mkdir(parents=True, exist_ok=True)

    # T212 expects ISO 8601 timestamps. If user passes YYYY-MM-DD, expand to full UTC timestamps.
    if len(time_from) == 10 and time_from.count("-") == 2:
        time_from = f"{time_from}T00:00:00Z"
    if len(time_to) == 10 and time_to.count("-") == 2:
        time_to = f"{time_to}T23:59:59Z"

    async with AsyncT212Client() as client:
        print(f"Base URL: {T212_BASE_URL}")
        rid = await client.request_history_export(
            time_from=time_from,
            time_to=time_to,
            include_orders=include_orders,
            include_transactions=include_transactions,
            include_dividends=include_dividends,
            include_interest=include_interest,
        )
        print(f"Requested export reportId={rid}. Polling status...")

        download_link: str | None = None
        status: str | None = None
        while True:
            exports = await client.list_history_exports()
            row = next((r for r in exports if int(r.get("reportId", -1)) == rid), None)
            if isinstance(row, dict):
                status = str(row.get("status") or "")
                download_link = row.get("downloadLink") if isinstance(row.get("downloadLink"), str) else None
                print(f"  status={status}")
                if status == "Finished" and download_link:
                    break
                if status in {"Failed", "Canceled"}:
                    raise RuntimeError(f"Export {rid} ended with status={status}")
            await asyncio.sleep(max(float(poll_every_sec), 1.0))

    out_path = out_dir / f"t212_history_export_{rid}_{stamp}.csv"
    print(f"Downloading CSV to {out_path} ...")
    await _download(download_link, out_path)  # type: ignore[arg-type]
    print("Done.")
    return out_path


def main() -> None:
    p = argparse.ArgumentParser(description="Request Trading 212 broker CSV export and download it.")
    p.add_argument("--from", dest="time_from", required=True, help="Start time (e.g. 2024-01-01 or ISO8601).")
    p.add_argument("--to", dest="time_to", required=True, help="End time (e.g. 2026-04-01 or ISO8601).")
    p.add_argument("--out", dest="out_dir", type=Path, default=Path("exports"), help="Output directory.")
    p.add_argument("--poll-every", type=float, default=20.0, help="Poll interval seconds (GET exports is 1/min).")
    p.add_argument("--no-orders", action="store_true", help="Exclude orders from report.")
    p.add_argument("--no-transactions", action="store_true", help="Exclude transactions from report.")
    p.add_argument("--no-dividends", action="store_true", help="Exclude dividends from report.")
    p.add_argument("--include-interest", action="store_true", help="Include interest in report.")
    args = p.parse_args()

    asyncio.run(
        run(
            time_from=args.time_from,
            time_to=args.time_to,
            out_dir=args.out_dir,
            poll_every_sec=args.poll_every,
            include_orders=not args.no_orders,
            include_transactions=not args.no_transactions,
            include_dividends=not args.no_dividends,
            include_interest=bool(args.include_interest),
        )
    )


if __name__ == "__main__":
    main()

