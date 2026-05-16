from __future__ import annotations

from ichimoku_framework.data.loaders import timeframe_to_upstox_v3


def test_timeframe_to_upstox_minutes() -> None:
    assert timeframe_to_upstox_v3("15min") == ("minutes", "15")


def test_timeframe_to_upstox_day() -> None:
    assert timeframe_to_upstox_v3("1d") == ("days", "1")
