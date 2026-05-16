from __future__ import annotations

import pandas as pd

from ichimoku_framework.config.models import StrategyConfig
def stop_and_target(entry_price: float, row: pd.Series, config: StrategyConfig) -> tuple[float | None, float | None]:
    """Build Pine-compatible long-style SL/TP levels with optional ATR extensions."""
    atr = row.get("atr")
    stop_distance = entry_price * abs(config.stop_loss_percent) / 100 if config.stop_loss_percent is not None and config.stop_loss_percent < 0 else None
    target_distance = entry_price * config.take_profit_percent / 100 if config.take_profit_percent is not None and config.take_profit_percent > 0 else None
    if config.atr_stop_multiplier is not None and pd.notna(atr):
        atr_stop = float(atr) * config.atr_stop_multiplier
        stop_distance = max(stop_distance or 0.0, atr_stop)
    if config.atr_take_profit_multiplier is not None and pd.notna(atr):
        atr_target = float(atr) * config.atr_take_profit_multiplier
        target_distance = max(target_distance or 0.0, atr_target)
    return (
        entry_price - stop_distance if stop_distance is not None else None,
        entry_price + target_distance if target_distance is not None else None,
    )
