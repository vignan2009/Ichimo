from __future__ import annotations

import pandas as pd


def donchian_midpoint(high: pd.Series, low: pd.Series, period: int) -> pd.Series:
    """Return the midpoint of the rolling Donchian channel."""
    return (high.rolling(period).max() + low.rolling(period).min()) / 2.0


def average_true_range(frame: pd.DataFrame, period: int) -> pd.Series:
    """Return Wilder-style ATR using an exponential moving average."""
    previous_close = frame["close"].shift(1)
    true_range = pd.concat(
        [
            frame["high"] - frame["low"],
            (frame["high"] - previous_close).abs(),
            (frame["low"] - previous_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return true_range.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()


def ichimoku(frame: pd.DataFrame, tenkan_period: int, kijun_period: int, senkou_b_period: int, displacement: int) -> pd.DataFrame:
    """Calculate Ichimoku lines without leaking future cloud values into decisions."""
    out = frame.copy()
    out["tenkan"] = donchian_midpoint(out["high"], out["low"], tenkan_period)
    out["kijun"] = donchian_midpoint(out["high"], out["low"], kijun_period)
    out["senkou_a_raw"] = (out["tenkan"] + out["kijun"]) / 2.0
    out["senkou_b_raw"] = donchian_midpoint(out["high"], out["low"], senkou_b_period)
    out["senkou_a"] = out["senkou_a_raw"].shift(displacement - 1)
    out["senkou_b"] = out["senkou_b_raw"].shift(displacement - 1)
    out["chikou"] = out["close"].shift(-displacement)
    return out
