# Advanced Alpha Research — Findings (v4 phase)

Rigorous out-of-sample test of five advanced concepts, judged on a
validation/holdout split (tune on validation, confirm on the untouched
holdout). Baseline = production **BEST_SAFE**: **+32.5% full-year OOS,
-10.1% max DD, Sharpe 1.83, +9.66% holdout**, after-tax €3,150 (10% CGT).

The honest headline: **the production config is near the no-leverage efficient
frontier. Three of four testable ideas overfit and hurt OOS results; one
(Kelly-weighted caps) traded return for robustness but via a questionable
allocation. Nothing cleanly beat the baseline on profit.** This reinforces the
core anti-overfit lesson — added complexity degrades a well-built system.

## Results by idea

| Idea | Module | Result vs baseline | Verdict |
|---|---|---|---|
| #1 GMM probabilistic regime | `regime_gmm.py`, `optimize3.py` | Full +14.8% / Holdout +2.3% / Sharpe 1.06 (best variant) | **Worse** — binary breadth filter wins |
| #2 Information Coefficient | `ic_analysis.py` | Model IC +0.015 (5-bar), +0.023 (15-bar), IR ~0.75 | **Diagnostic** — confirms modest real edge; predicted macro overfit |
| #3a Kelly on risk-% | `kelly_sizing.py`, `optimize4.py` | Identical to baseline | **No effect** — position cap binds, not risk % |
| #3b Kelly on position caps | `optimize6.py` | Full +26.7% / Holdout **+13.1%** / DD **-8.1%** / Sharpe 1.87 | **Mixed** — better holdout & DD, lower full-year; starves proven winners |
| #4 Cross-asset/macro features | `optimize5.py` | Full +14.4% / Holdout -1.2% / Sharpe 1.01 | **Worse** — low-IC features overfit in-sample |
| #5 Reinforcement learning (PPO) | — | Not implemented | **Infeasible** — no torch/gym; would overfit on 5y data |

## Why each negative result is informative

- **GMM regime**: For a structural-bull trend follower you *want* full conviction
  whenever breadth is positive. Probabilistic blending (mean OOS multiplier ~1.8
  vs binary ~3.5) diluted conviction without improving crash-timing. The binary
  EMA200-breadth rule the bot already uses is better here.

- **IC analysis**: Model IC is modest but real and *stronger at 15 bars than 5*,
  which validates the swing-holding design. It also flagged that market-context
  features have weak short-horizon IC — correctly predicting #4 would overfit.

- **Kelly on risk-%**: Mathematically inert in the aggressive config because the
  per-symbol position cap is the binding constraint, not the risk fraction.

- **Kelly on position caps**: The only idea to beat the baseline on the unseen
  holdout (+13.1% vs +9.66%) with lower DD (-8.1%) and val≈holdout consistency
  (less overfit signature). BUT it down-weights ASML, MC, HO, SAF — the
  structurally strongest, best OOS performers — based on in-sample Kelly edge.
  Its lower DD is really just diversification away from concentrated winners.
  Betting against those names forward is hard to justify, so it is documented as
  an experimental option, not adopted as default.

- **Macro features**: Adding 6 universe-context columns dropped holdout to -1.2%.
  Classic overfitting from low-signal features — exactly what the IC analysis
  warned about.

## What was kept

- Engine hooks (all optional, default off): `regime_risk_series`,
  `symbol_risk_override`, `symbol_cap_override` — available for future research.
- `ic_analysis.py` as an ongoing model-quality / feature-pruning diagnostic.
- **Production config unchanged: BEST_SAFE remains the recommended deployment.**

## How to reproduce
```
python -m new_trading212bot.optimize2 --rebuild   # build comprehensive cache
python -m new_trading212bot.ic_analysis           # model & feature IC
python -m new_trading212bot.optimize3             # GMM regime
python -m new_trading212bot.optimize4             # Kelly on risk-%
python -m new_trading212bot.optimize5             # macro features (retrains)
python -m new_trading212bot.optimize6             # Kelly on position caps
```
