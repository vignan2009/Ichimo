from __future__ import annotations

import pandas as pd

from ichimoku_framework.backtest.engine import BacktestEngine
from ichimoku_framework.config.models import BacktestConfig, StrategyConfig
from ichimoku_framework.strategy.models import ExitReason


def _candles() -> pd.DataFrame:
    index = pd.date_range("2024-01-01 09:15", periods=60, freq="5min")
    frame = pd.DataFrame(
        {
            "open": range(100, 160),
            "high": range(101, 161),
            "low": range(99, 159),
            "close": range(100, 160),
        },
        index=index,
    )
    return frame


def test_engine_runs_without_lookahead_failure() -> None:
    result = BacktestEngine(StrategyConfig(), BacktestConfig()).run(_candles())
    assert len(result.equity_curve) == 60


def test_stop_loss_has_priority_over_take_profit() -> None:
    frame = _candles()
    config = StrategyConfig(stop_loss_percent=-1.0, take_profit_percent=1.0)
    engine = BacktestEngine(config, BacktestConfig(quantity=1))
    prepared = engine.prepare(frame)
    last = prepared.iloc[-1].copy()
    timestamp = prepared.index[-1]
    from ichimoku_framework.strategy.models import Position, Side
    from ichimoku_framework.strategy.state_machine import TradeState

    state = TradeState(config)
    state.position = Position(
        side=Side.LONG,
        entry_time=timestamp.to_pydatetime(),
        entry_price=100.0,
        quantity=1,
        stop_loss=99.0,
        take_profit=101.0,
    )
    last["low"] = 98.0
    last["high"] = 102.0
    engine._process_exit(timestamp, last, state, bars_in_trade=1)
    assert state.trades[0].reason == ExitReason.STOP_LOSS
