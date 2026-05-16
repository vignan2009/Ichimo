from __future__ import annotations

from pathlib import Path

from ichimoku_framework.analytics.dashboard import build_dashboard
from ichimoku_framework.analytics.performance import summarize
from ichimoku_framework.backtest.engine import BacktestEngine
from ichimoku_framework.backtest.realistic import RealisticBacktestEngine
from ichimoku_framework.config.models import AppConfig
from ichimoku_framework.data.loaders import load_ohlc_csv


def main() -> None:
    config = AppConfig.from_yaml("config/example_strategy.yaml")
    candles = load_ohlc_csv("sample_data/nifty_sample.csv")
    result = BacktestEngine(config.strategy, config.backtest).run(candles)
    print(summarize(result.trades, result.equity_curve))
    Path("artifacts").mkdir(exist_ok=True)
    build_dashboard(result.candles, result.trades, result.equity_curve).write_html("artifacts/dashboard.html")
    realistic = RealisticBacktestEngine(config.strategy, config.backtest).run(candles)
    print(summarize(realistic.trades, realistic.equity_curve))


if __name__ == "__main__":
    main()
