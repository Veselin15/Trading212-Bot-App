# new_trading212bot

ML-driven live/paper trader for Trading 212 (EU + US universe).

## Quick start

1. Copy `.env.example` to repo root `.env` and set `T212_API_KEY` (demo URL by default).
2. Install deps: `pip install -r new_trading212bot/requirements.txt`
3. Dry run: `python start_bot.py --once --dry-run`
4. Paper: `python start_bot.py`

## Layout

| Module | Role |
|--------|------|
| `live_trader.py` | Main loop (15m entries, 5m poll) |
| `trade_audit.py` | Structured audit log (`logs/live_audit.jsonl`) |
| `config.py` | Universe, risk, and strategy constants |
| `strategy.py` / `backtest.py` | Signal logic and walk-forward backtest |
| `models/` | Per-symbol XGBoost / ensemble checkpoints |
| `run_pipeline.py` | Train models from `data/` CSVs |

State is persisted in `live_state.json`; cycle logs go to `logs/live_trader.log`.
