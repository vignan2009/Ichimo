from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class LiveRiskManager:
    max_daily_loss: float
    max_open_positions: int = 1
    realized_pnl: float = 0.0
    open_positions: int = 0

    def can_submit(self) -> bool:
        return self.realized_pnl > -self.max_daily_loss and self.open_positions < self.max_open_positions

