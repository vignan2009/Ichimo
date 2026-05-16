from __future__ import annotations

import pandas as pd

from ichimoku_framework.indicators.signals import classify_crosses
from ichimoku_framework.strategy.logic import entry_decision
from ichimoku_framework.config.models import StrategyConfig


def test_bullish_cross_classification() -> None:
    frame = pd.DataFrame(
        {
            "close": [10, 11],
            "tenkan": [9, 12],
            "kijun": [10, 10],
            "senkou_a": [8, 8],
            "senkou_b": [9, 9],
        }
    )
    result = classify_crosses(frame)
    assert bool(result.loc[1, "bullish_cross"])
    assert result.loc[1, "bullish_class"] == "strong"


def test_missing_signal_classes_are_false_not_ambiguous() -> None:
    row = pd.Series(
        {
            "entry_bullish_class": pd.NA,
            "entry_bearish_class": pd.NA,
        }
    )
    assert entry_decision(row, StrategyConfig()).triggered is False
