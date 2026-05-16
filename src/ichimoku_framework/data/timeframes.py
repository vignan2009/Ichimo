from __future__ import annotations

import pandas as pd


def resample_ohlc(candles: pd.DataFrame, rule: str) -> pd.DataFrame:
    """Create a higher-timeframe OHLC series without forward-looking aggregation."""
    return candles.resample(rule, label="right", closed="right").agg(
        {"open": "first", "high": "max", "low": "min", "close": "last"}
    ).dropna()
