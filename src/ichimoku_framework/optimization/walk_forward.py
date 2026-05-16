from __future__ import annotations

from collections.abc import Callable

import pandas as pd

from ichimoku_framework.analytics.performance import PerformanceSummary, summarize
from ichimoku_framework.backtest.engine import BacktestEngine
from ichimoku_framework.config.models import BacktestConfig, StrategyConfig


def walk_forward(
    candles: pd.DataFrame,
    train_bars: int,
    test_bars: int,
    selector: Callable[[pd.DataFrame], StrategyConfig],
    backtest_config: BacktestConfig,
) -> list[PerformanceSummary]:
    """Run rolling train/test windows using a caller-supplied parameter selector."""
    summaries: list[PerformanceSummary] = []
    start = 0
    while start + train_bars + test_bars <= len(candles):
        train = candles.iloc[start : start + train_bars]
        test = candles.iloc[start + train_bars : start + train_bars + test_bars]
        strategy = selector(train)
        result = BacktestEngine(strategy, backtest_config).run(test)
        summaries.append(summarize(result.trades, result.equity_curve))
        start += test_bars
    return summaries

