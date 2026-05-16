from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class Side(str, Enum):
    LONG = "long"
    SHORT = "short"


class ExitReason(str, Enum):
    STOP_LOSS = "stop_loss"
    TAKE_PROFIT = "take_profit"
    CLOSE_SIGNAL = "close_signal"


@dataclass(slots=True)
class Position:
    side: Side
    entry_time: datetime
    entry_price: float
    quantity: int
    stop_loss: float | None
    take_profit: float | None


@dataclass(slots=True)
class Trade:
    side: Side
    entry_time: datetime
    exit_time: datetime
    entry_price: float
    exit_price: float
    quantity: int
    pnl: float
    pnl_percent: float
    bars_held: int
    reason: ExitReason
