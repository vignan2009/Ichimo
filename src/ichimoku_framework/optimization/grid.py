from __future__ import annotations

from itertools import product
from typing import Iterable

import pandas as pd

from ichimoku_framework.analytics.performance import PerformanceSummary, summarize
from ichimoku_framework.backtest.engine import BacktestEngine
from ichimoku_framework.config.models import BacktestConfig, StrategyConfig


def grid_search(
    candles: pd.DataFrame,
    base_strategy: StrategyConfig,
    backtest_config: BacktestConfig,
    tenkan_values: Iterable[int],
    kijun_values: Iterable[int],
) -> list[tuple[StrategyConfig, PerformanceSummary]]:
    results: list[tuple[StrategyConfig, PerformanceSummary]] = []
    for tenkan, kijun in product(tenkan_values, kijun_values):
        strategy = base_strategy.model_copy(
            update={"entry_tenkan_period": tenkan, "entry_kijun_period": kijun}
        )
        result = BacktestEngine(strategy, backtest_config).run(candles)
        results.append((strategy, summarize(result.trades, result.equity_curve)))
    return results


def bayesian_optimization_hook() -> None:
    """Extension point for Optuna, skopt, or an internal optimizer."""
