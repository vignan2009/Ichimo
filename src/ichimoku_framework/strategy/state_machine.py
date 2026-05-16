from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from ichimoku_framework.config.models import StrategyConfig
from ichimoku_framework.strategy.models import Position, Trade


@dataclass(slots=True)
class TradeState:
    config: StrategyConfig
    position: Position | None = None
    trades: list[Trade] = field(default_factory=list)
    daily_realized_pnl: dict[date, float] = field(default_factory=dict)

    def can_open(self, trading_day: date) -> bool:
        if self.position is not None or self.config.max_concurrent_trades < 1:
            return False
        if self.config.max_daily_loss is None:
            return True
        return self.daily_realized_pnl.get(trading_day, 0.0) > -self.config.max_daily_loss

    def close(self, trade: Trade) -> None:
        self.trades.append(trade)
        self.daily_realized_pnl[trade.exit_time.date()] = self.daily_realized_pnl.get(trade.exit_time.date(), 0.0) + trade.pnl
        self.position = None

