# Deployment Guide — v4.0 (BEST_SAFE)

The live bot ships with the optimized **BEST_SAFE** production config wired in.
Backtested out-of-sample (1-year, €10k, 10% CGT): **+32.5% return, −10.1% max
drawdown, Sharpe 1.83, +9.66% on the untouched holdout half.**

## What's running

`production.py` is the single source of truth. The live trader uses:
- **Strategy**: `SwingStrategyV3` — trend-scaled take-profit (TP widens to 6–7
  ATR in strong ADX trends) + breakout-tight stops + all v2 quality filters
  (volatility-spike guard, RSI gate, session guards, asymmetric time exit).
- **Sizing**: bull-tilt regime scaling (4.2× in a broad uptrend, 0.7× in a
  downtrend), 5 concurrent slots, 98% max exposure, position cap 0.90,
  risk cap 0.75.
- **Universe**: 25 EU stocks minus the validation-derived blocklist
  (`ALV.DE`, `SIE.DE`, `TTE.PA`).
- **Safety**: daily circuit breaker + drawdown position scaler ON (the "safe"
  mode — gives up ~1pp of return vs raw max-profit for an automatic brake).

## First-time setup

```bash
# 1. (deployment env) install deps (run from Server-App/ directory)
pip install -r t212_miner_bot/requirements.txt

# 2. set Trading212 credentials (demo by default)
#    T212_API_KEY=...   T212_BASE_URL=https://demo.trading212.com
#    optional: TWELVEDATA_API_KEY, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
cp .env.example .env   # then edit

# 3. train the models on the current feature pipeline (REQUIRED — the models
#    must match the code; this reproduces the backtested config)
python -m t212_miner_bot.train_production_models
```

## Run

```bash
# Dry run — computes signals, places NO orders (verify the pipeline first)
python -m t212_miner_bot.live_trader --dry-run

# Read-only ranked signal report for today
python -m t212_miner_bot.live_signal

# Live paper trading (demo account) once you're satisfied
python -m t212_miner_bot.live_trader
```

## Verify / reproduce the backtest

```bash
python -m t212_miner_bot.optimize2 --rebuild   # rebuild model+score cache
python -m t212_miner_bot.finalize              # prints the BEST_SAFE numbers
```

## Maintenance

- **Retrain periodically** (e.g. monthly) as new data arrives:
  `python -m t212_miner_bot.train_production_models`
- **Re-derive the blocklist** when retraining a lot of new data:
  `python -m t212_miner_bot.optimize2 --rebuild` then update
  `PRODUCTION_BLOCKLIST` in `production.py`.
- To trade the slightly higher-return / no-brake variant, call
  `production.build_engine(mode="max_profit")` (backtest only — not recommended
  live).

See `RESEARCH_NOTES.md` for the full optimization history and why the advanced
ideas (GMM regime, macro features, Kelly) were tested and not adopted.
