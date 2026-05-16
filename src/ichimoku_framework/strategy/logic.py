from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from ichimoku_framework.config.models import ConditionMode, StrategyConfig
@dataclass(frozen=True, slots=True)
class SignalDecision:
    triggered: bool
    values: tuple[bool, ...]


def _reduce_conditions(conditions: list[bool], mode: ConditionMode) -> bool:
    return any(conditions) if mode == ConditionMode.ANY else all(conditions)


def _six_signal_values(row: pd.Series, prefix: str, bullish_classes: set[str], bearish_classes: set[str]) -> tuple[bool, ...]:
    return (
        row.get(f"{prefix}bullish_class") == "strong" and "strong" in bullish_classes,
        row.get(f"{prefix}bullish_class") == "neutral" and "neutral" in bullish_classes,
        row.get(f"{prefix}bullish_class") == "weak" and "weak" in bullish_classes,
        row.get(f"{prefix}bearish_class") == "strong" and "strong" in bearish_classes,
        row.get(f"{prefix}bearish_class") == "neutral" and "neutral" in bearish_classes,
        row.get(f"{prefix}bearish_class") == "weak" and "weak" in bearish_classes,
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
