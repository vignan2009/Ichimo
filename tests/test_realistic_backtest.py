from __future__ import annotations

import pandas as pd

from ichimoku_framework.backtest.realistic import PendingEntry, RealisticBacktestEngine
from ichimoku_framework.config.models import BacktestConfig, StrategyConfig
from ichimoku_framework.strategy.models import ExitReason, Position, Side
from ichimoku_framework.strategy.state_machine import TradeState


def _candles() -> pd.DataFrame:
    index = pd.date_range("2024-01-01 09:15", periods=3, freq="5min")
    return pd.DataFrame(
        {
            "open": [100, 101, 102],
            "high": [101, 103, 103],
            "low": [99, 100, 101],
            "close": [100, 102, 102],
        },
        index=index,
    )


def test_realistic_close_applies_round_trip_costs() -> None:
    config = StrategyConfig(stop_loss_percent=-1.0, take_profit_percent=1.0)
    engine = RealisticBacktestEngine(config, BacktestConfig(quantity=2, commission_per_order=20))
    state = TradeState(config)
    state.position = Position(
        side=Side.LONG,
        entry_time=_candles().index[0].to_pydatetime(),
        entry_price=100.0,
        quantity=2,
        stop_loss=99.0,
        take_profit=101.0,
    )
    engine._close_position(_candles().index[1], _candles().iloc[1], state, 1, ExitReason.TAKE_PROFIT, 101.0, "bar_touch")
    assert state.trades[0].gross_pnl == 2.0
    assert state.trades[0].costs == 40.0
    assert state.trades[0].pnl == -38.0


def test_pending_entry_shape() -> None:
    pending = PendingEntry(_candles().index[0], 1)
    assert pending.delay_remaining == 1
