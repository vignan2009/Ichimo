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
    END_OF_DAY = "end_of_day"


@dataclass(slots=True)
class Position:
    side: Side
    entry_time: datetime
    entry_price: float
    quantity: int
    stop_loss: float | None
    take_profit: float | None
    signal_time: datetime | None = None
    raw_entry_price: float | None = None
    entry_bar_index: int | None = None


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
    signal_time: datetime | None = None
    raw_entry_price: float | None = None
    gross_pnl: float | None = None
    costs: float = 0.0
    exit_basis: str | None = None
