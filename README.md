# Ichimoku Trading Framework

Production-oriented Python scaffold for Ichimoku research, realistic sequential backtesting, and Upstox execution integration.

## What is implemented

- Modular Ichimoku indicators and cloud-strength classification
- Single-position state machine with long/short support
- Sequential candle processing with intrabar priority: stop loss, take profit, then close signal
- Worst-case handling when stop and target are both touched in the same candle
- Percent and optional ATR-expanded protective levels
- Daily loss guard, session filter, slippage, commissions
- Analytics summary and Plotly dashboard
- Upstox REST adapter, retryable order manager, and Indian options contract selection helper
- Alert-event surface, websocket/risk-management scaffolding, and premium slippage helper
- Grid-search hooks, walk-forward testing, higher-timeframe resampling, and a Bayesian optimization extension point

## Pine parity notes

The strategy layer now mirrors the supplied Skyrexio Pine Script semantics:

- separate ENTRY and CLOSE Ichimoku parameter sets
- cloud classification based on the Tenkan value on the cross bar
- Pine displacement convention using `displacement - 1`
- six booleans pushed into ENTRY/CLOSE arrays and reduced with `ANY` or `ALL`
- one open trade at a time
- bearish entry signals can still trigger the same single long-style trade, exactly like the script
- percentage stats use `(exit - entry) / entry * 100`
- intrabar exit priority is `stop loss`, then `take profit`, then close signal

## Backtest modes

- `BacktestEngine`: Pine-exact behavior for TradingView reconciliation
- `RealisticBacktestEngine`: delayed next-open fills, adverse point slippage, conservative same-candle handling, no-new-entry cutoff, and end-of-day flattening inspired by the reference `nifty` research engine

## Setup

```bash
python -m pip install -r requirements.txt
$env:PYTHONPATH = "src"
python examples/run_backtest.py
```

The example writes an interactive dashboard to `artifacts/dashboard.html`.

## Upstox integration

The project loads environment variables from a root `.env` file. The live adapter expects the same Upstox names used by the `nifty` project:

- `UPSTOX_API_KEY`
- `UPSTOX_CLIENT_ID`
- `UPSTOX_API_SECRET`
- `UPSTOX_ACCESS_TOKEN`
- `REDIRECT_URI`

The client exposes:

- historical candle fetches
- option-chain fetches
- V3 order placement

The current official Upstox surface used here includes instrument metadata, historical candles, V3 market feed, option chain, and V3 order placement. Keep auth/token refresh and websocket lifecycle management in the live application layer around the provided adapters.

## Project layout

```text
config/                  YAML configuration
examples/                runnable examples
sample_data/             sample OHLC input
src/ichimoku_framework/
  analytics/             metrics and dashboard
  backtest/              sequential execution engine
  config/                pydantic config models
  data/                  data loaders
  execution/             Upstox and live-order helpers
  indicators/            Ichimoku and signal classification
  optimization/          grid-search hooks
  strategy/              decisions, risk, state machine
tests/                   unit tests
```

## Golden-master validation

For final numerical reconciliation, export TradingView bar data and alert timestamps from the same symbol/timeframe. Comparing those outputs against this engine is the right next step before trusting live deployment.
