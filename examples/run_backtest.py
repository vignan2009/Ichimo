from __future__ import annotations

from pathlib import Path
from datetime import datetime

from ichimoku_framework.analytics.dashboard import build_dashboard
from ichimoku_framework.analytics.performance import summarize
from ichimoku_framework.analytics.reporting import export_excel_report
from ichimoku_framework.backtest.engine import BacktestEngine
from ichimoku_framework.backtest.realistic import RealisticBacktestEngine
from ichimoku_framework.config.models import AppConfig
from ichimoku_framework.data.loaders import load_ohlc_csv, load_upstox_ohlc
from ichimoku_framework.execution.upstox_client import UpstoxClient


def main() -> None:
    config = AppConfig.from_yaml("config/example_strategy.yaml")
    if config.data.source == "upstox":
        candles = load_upstox_ohlc(
            UpstoxClient(config.upstox),
            instrument_key=config.data.instrument_key,
            timeframe=config.data.timeframe,
            from_date=config.data.from_date,
            to_date=config.data.to_date,
        )
    else:
        candles = load_ohlc_csv(config.data.csv_path)
    result = BacktestEngine(config.strategy, config.backtest).run(candles)
    pine_summary = summarize(result.trades, result.equity_curve)
    print(pine_summary)
    Path("artifacts").mkdir(exist_ok=True)
    build_dashboard(result.candles, result.trades, result.equity_curve).write_html("artifacts/dashboard.html")
    realistic = RealisticBacktestEngine(config.strategy, config.backtest).run(candles)
    realistic_summary = summarize(realistic.trades, realistic.equity_curve)
    print(realistic_summary)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = export_excel_report(
        Path("artifacts") / f"ichimoku_backtest_{timestamp}.xlsx",
        config,
        result,
        realistic,
        pine_summary,
        realistic_summary,
    )
    print(f"Excel report written to {report_path}")


if __name__ == "__main__":
    main()
