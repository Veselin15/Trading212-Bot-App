# Server-App

Legacy standalone bot code. **Only the core package is used at runtime:**

- `t212_miner_bot/` — imported by `backend/app/strategy/t212_miner_runner.py` for live signal generation (`data_feed`, `config`, `indicators`).

The standalone `main.py` entry point is not part of the MVP stack. Do not run it alongside `dev.ps1`.

Runtime state files (`state*.json`, `.bot_runtime.lock`) are gitignored.
