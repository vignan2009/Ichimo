from __future__ import annotations

import pandas as pd

from ichimoku_framework.indicators.signals import classify_crosses


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

