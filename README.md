# Ichimoku Trading Framework

Python research framework for the supplied Skyrexio Ichimoku Pine strategy, with TradingView-parity validation, more realistic execution models, Upstox integration, and report generation.

## Current State

- Default underlying: `NSE_INDEX|Nifty 50`
- Default data source: Upstox V3 historical candles
- Default timeframe: `15min`
- Default test window: April 2026
- Primary config: `config/example_strategy.yaml`
- Main runner: `examples/run_backtest.py`
- Market-time assumptions: `Asia/Kolkata`

The project currently supports:

- Pine-exact Ichimoku signal reproduction
- sequential candle-by-candle execution
- intrabar SL/TP checks with worst-case SL priority
- Plotly dashboard export
- Excel workbook export
- Upstox REST adapters
- a realistic spot-proxy engine
- an overnight ATM option-premium engine

## Strategy Logic

The signal layer mirrors the supplied Pine script:

- separate ENTRY and CLOSE Ichimoku parameter sets
- Tenkan/Kijun cross detection
- cross strength classified as `strong`, `neutral`, or `weak`
- cloud comparison uses the Tenkan value on the cross bar
- Pine displacement convention uses `displacement - 1`
- six enabled booleans per side reduced with `ANY` or `ALL`

Current config enables:

- strong bullish entry
- strong bearish entry
- strong bullish close
- strong bearish close

Current exits:

- stop loss: `-2%`
- take profit: `+5%`

Important distinction:

- The **Pine-exact** engine preserves the original script's odd single long-style trade state even when bearish entry signals fire.
- The **options** engine uses tradable direction instead: bullish signal buys ATM `CE`, bearish signal buys ATM `PE`.

## Backtest Modes

| Mode | Purpose | Entry model | Holding model | PnL basis |
| --- | --- | --- | --- | --- |
| `BacktestEngine` | TradingView reconciliation | same-bar close | multi-day allowed | underlying spot proxy |
| `RealisticBacktestEngine` | intraday execution stress test | next-bar open with adverse point slippage | forced EOD exit | underlying spot proxy |
| `OvernightOptionBacktestEngine` | intended tradable option path | next-bar option premium open | overnight allowed | option premium |

What each mode means:

- `BacktestEngine` is for proving we matched Pine, not for trusting deployment economics.
- `RealisticBacktestEngine` intentionally behaves like an intraday study and is useful for checking how much same-close optimism matters.
- `OvernightOptionBacktestEngine` is the first mode aligned with the current intended trade expression: ATM options that may stay open overnight until close signal, premium SL/TP, expiry, or end of test.

## Latest Research Read

The first April 2026 one-month NIFTY spot-proxy run showed:

- Pine-exact mode: positive
- realistic intraday mode: negative

The workbook made the reason clear:

- Pine-exact held positions for multiple days
- realistic mode force-closed every trade at end of day

That means the earlier comparison mixed a swing strategy with an intraday strategy. The next meaningful execution read should come from the overnight options engine, followed by longer-period validation and true futures testing.

Current strategy is **not validated** yet.

## Outputs

Each run writes:

- dashboard: `artifacts/dashboard.html`
- Excel report: `artifacts/ichimoku_backtest_<timestamp>.xlsx`

Excel sheets:

- `Summary`
- `Trades_PineExact`
- `Trades_Realistic`
- `Trades_OvernightOptions` when enabled
- `Daily_PnL`
- `Monthly_Returns`
- `Equity_Curves`
- `Config`

## Setup

### Local Windows

```powershell
python -m pip install -r requirements.txt
$env:PYTHONPATH = "src"
python examples/run_backtest.py
```

### Ubuntu VPS

```bash
git clone https://github.com/vignan2009/Ichimo.git
cd Ichimo
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python examples/run_backtest.py
```

Create `.env` manually on the VPS before running.

## Environment

The root `.env` is intentionally ignored by Git. Expected variables:

- `UPSTOX_API_KEY`
- `UPSTOX_CLIENT_ID`
- `UPSTOX_API_SECRET`
- `UPSTOX_ACCESS_TOKEN`
- `REDIRECT_URI`

The project keeps secrets out of Git. The reference-only `nifty/` folder is also ignored and is not part of this repository.

## Upstox Notes

Used Upstox surfaces:

- V3 historical candles for underlying data
- option contracts / option chain
- expired-instruments expiries
- expired option contracts
- expired historical candles
- V3 order placement scaffold

Historical backtests for expired option contracts use Upstox expired-instruments APIs. Those APIs are documented by Upstox as Plus-plan endpoints, so expired option-premium backtests require account access to that API family.

## Project Layout

```text
config/                  YAML configuration
examples/                runnable workflows
sample_data/             offline CSV fallback
src/ichimoku_framework/
  analytics/             metrics, dashboard, Excel reports
  backtest/              Pine, realistic, and overnight-option engines
  config/                pydantic config models
  data/                  CSV and Upstox loaders
  execution/             Upstox adapters and option helpers
  indicators/            Ichimoku calculations and classifications
  optimization/          grid and walk-forward hooks
  strategy/              decisions, risk, state models
tests/                   focused unit coverage
memory.md                handoff notes for future chats
```

## Next Priorities

1. Run the overnight options mode on real expired premium data.
2. Add true futures backtesting.
3. Expand validation beyond one month to at least `1-2` years.
4. Compare Pine-exact, overnight options, and futures on the same signal set.
5. Add TradingView golden-master tests from exported alerts/signals before trusting live use.

## Caution

This is research infrastructure, not a validated production strategy yet. A profitable Pine-equivalent run is only the start; tradable results depend on actual instrument selection, fill model, slippage, costs, expiry handling, and enough out-of-sample history.
