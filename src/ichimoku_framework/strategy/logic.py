from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

import pandas as pd

from ichimoku_framework.config.models import ConditionMode, StrategyConfig
@dataclass(frozen=True, slots=True)
class SignalDecision:
    triggered: bool
    values: tuple[bool, ...]


class EntryDirection(str, Enum):
    BULLISH = "bullish"
    BEARISH = "bearish"


def _reduce_conditions(conditions: list[bool], mode: ConditionMode) -> bool:
    return any(conditions) if mode == ConditionMode.ANY else all(conditions)


def _six_signal_values(row: pd.Series, prefix: str, bullish_classes: set[str], bearish_classes: set[str]) -> tuple[bool, ...]:
    bullish_class = row.get(f"{prefix}bullish_class")
    bearish_class = row.get(f"{prefix}bearish_class")
    bullish_value = None if pd.isna(bullish_class) else str(bullish_class)
    bearish_value = None if pd.isna(bearish_class) else str(bearish_class)
    return (
        bullish_value == "strong" and "strong" in bullish_classes,
        bullish_value == "neutral" and "neutral" in bullish_classes,
        bullish_value == "weak" and "weak" in bullish_classes,
        bearish_value == "strong" and "strong" in bearish_classes,
        bearish_value == "neutral" and "neutral" in bearish_classes,
        bearish_value == "weak" and "weak" in bearish_classes,
    )


def entry_decision(row: pd.Series, config: StrategyConfig) -> SignalDecision:
    values = _six_signal_values(
        row,
        "entry_",
        {item.value for item in config.enabled_entry_bullish_classes},
        {item.value for item in config.enabled_entry_bearish_classes},
    )
    return SignalDecision(triggered=_reduce_conditions(list(values), config.entry_condition_mode), values=values)


def close_decision(row: pd.Series, config: StrategyConfig) -> SignalDecision:
    values = _six_signal_values(
        row,
        "close_",
        {item.value for item in config.enabled_close_bullish_classes},
        {item.value for item in config.enabled_close_bearish_classes},
    )
    return SignalDecision(triggered=_reduce_conditions(list(values), config.close_condition_mode), values=values)


def directional_entry(row: pd.Series, config: StrategyConfig) -> EntryDirection | None:
    """Return the tradable direction implied by the enabled entry signal."""
    bullish_classes = {item.value for item in config.enabled_entry_bullish_classes}
    bearish_classes = {item.value for item in config.enabled_entry_bearish_classes}
    bullish = row.get("entry_bullish_class")
    bearish = row.get("entry_bearish_class")
    bullish_value = None if pd.isna(bullish) else str(bullish)
    bearish_value = None if pd.isna(bearish) else str(bearish)
    if bullish_value in bullish_classes:
        return EntryDirection.BULLISH
    if bearish_value in bearish_classes:
        return EntryDirection.BEARISH
    return None
