from __future__ import annotations

from enum import Enum

import pandas as pd


class Direction(str, Enum):
    BULLISH = "bullish"
    BEARISH = "bearish"


class CloudStrength(str, Enum):
    STRONG = "strong"
    NEUTRAL = "neutral"
    WEAK = "weak"


def classify_crosses(frame: pd.DataFrame, prefix: str = "") -> pd.DataFrame:
    """Classify Pine-style Tenkan/Kijun crosses using Tenkan as signal value."""
    out = frame.copy()
    tenkan = out[f"{prefix}tenkan"]
    kijun = out[f"{prefix}kijun"]
    senkou_a = out[f"{prefix}senkou_a"]
    senkou_b = out[f"{prefix}senkou_b"]
    bullish_cross = (tenkan > kijun) & (tenkan.shift(1) <= kijun.shift(1))
    bearish_cross = (tenkan < kijun) & (tenkan.shift(1) >= kijun.shift(1))
    bullish_value = tenkan.where(bullish_cross)
    bearish_value = tenkan.where(bearish_cross)

    out[f"{prefix}bullish_cross"] = bullish_cross
    out[f"{prefix}bearish_cross"] = bearish_cross
    out[f"{prefix}bullish_class"] = pd.NA
    out[f"{prefix}bearish_class"] = pd.NA
    out.loc[(bullish_value > senkou_a) & (bullish_value > senkou_b), f"{prefix}bullish_class"] = CloudStrength.STRONG.value
    out.loc[
        ((bullish_value > senkou_a) & (bullish_value < senkou_b))
        | ((bullish_value < senkou_a) & (bullish_value > senkou_b)),
        f"{prefix}bullish_class",
    ] = CloudStrength.NEUTRAL.value
    out.loc[(bullish_value < senkou_a) & (bullish_value < senkou_b), f"{prefix}bullish_class"] = CloudStrength.WEAK.value
    out.loc[(bearish_value < senkou_a) & (bearish_value < senkou_b), f"{prefix}bearish_class"] = CloudStrength.STRONG.value
    out.loc[
        ((bearish_value > senkou_a) & (bearish_value < senkou_b))
        | ((bearish_value < senkou_a) & (bearish_value > senkou_b)),
        f"{prefix}bearish_class",
    ] = CloudStrength.NEUTRAL.value
    out.loc[(bearish_value > senkou_a) & (bearish_value > senkou_b), f"{prefix}bearish_class"] = CloudStrength.WEAK.value
    return out
