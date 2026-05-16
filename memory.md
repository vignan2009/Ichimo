# Project Memory

Read this first in a new chat.

## Project

Python framework for the Skyrexio Ichimoku Pine strategy with:

- Pine-exact signal/backtest parity mode
- Realistic execution mode inspired by the reference `nifty` project
- Upstox V3 historical candle loading
- Plotly dashboard output
- Future live-execution structure for Upstox

All market-time assumptions are currently oriented around `Asia/Kolkata`.

## Key Files

- `config/example_strategy.yaml`: main runnable config
- `examples/run_backtest.py`: fetches data, runs both backtest modes, writes artifacts
- `src/ichimoku_framework/backtest/engine.py`: Pine-exact engine
- `src/ichimoku_framework/backtest/realistic.py`: delayed next-open realistic engine
- `src/ichimoku_framework/analytics/`: summaries, dashboard, and reports
- `src/ichimoku_framework/execution/upstox_client.py`: Upstox REST adapter

## Current Strategy Facts

- Timeframe default: `15min`
- Data source default: Upstox V3 historical candles
- Instrument default: `NSE_INDEX|Nifty 50`
- ENTRY and CLOSE Ichimoku parameters are separate
- Current enabled ENTRY classes: strong bullish and strong bearish
- Current enabled CLOSE classes: strong bullish and strong bearish
- The Pine-exact engine preserves the original script's single long-style trade state even when bearish entry signals trigger
- Current Pine-configured exits: `-2%` stop loss and `+5%` take profit

## Backtest Modes

- `BacktestEngine`
  - mirrors TradingView-style same-close behavior
  - useful for Pine reconciliation only
- `RealisticBacktestEngine`
  - one-candle delayed next-open entry
  - adverse point slippage
  - conservative same-candle SL/TP resolution
  - no-new-entry cutoff
  - EOD flattening
  - this is the mode that matters more for deployment judgment

## Current Research Read

- One-month April 2026 NIFTY spot-proxy test:
  - Pine-exact result was positive
  - realistic result was negative
- The strategy is not yet validated.
- Current tests are still on spot/index proxy data, not true futures or true option premium backtests.

## Operational Notes

- `.env` is local only and ignored by Git.
- `nifty/` is reference-only and ignored by Git.
- GitHub repo exists for deployment sync.
- VPS setup is expected to create its own `.env`.
- Upstox token expiry can break remote historical-data runs.

## Next Priorities

1. Keep Excel and dashboard reporting current for each backtest run.
2. Add true futures and options backtesting instead of only spot-proxy research.
3. Build longer-period validation and side-by-side execution comparisons.
4. Add TradingView golden-master comparisons once exported reference signals are available.

## First Reads In A New Chat

1. `memory.md`
2. `README.md`
3. `config/example_strategy.yaml`
4. `examples/run_backtest.py`
5. `src/ichimoku_framework/backtest/engine.py`
6. `src/ichimoku_framework/backtest/realistic.py`
