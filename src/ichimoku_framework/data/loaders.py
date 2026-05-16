from __future__ import annotations

from pathlib import Path

import pandas as pd

from ichimoku_framework.execution.upstox_client import UpstoxClient


def load_ohlc_csv(path: str | Path) -> pd.DataFrame:
    """Load a CSV with timestamp/open/high/low/close columns."""
    frame = pd.read_csv(path, parse_dates=["timestamp"])
    return frame.set_index("timestamp").sort_index()


def timeframe_to_upstox_v3(timeframe: str) -> tuple[str, str]:
    """Translate common pandas-style aliases to Upstox V3 unit/interval values."""
    normalized = timeframe.strip().lower()
    if normalized.endswith("min"):
        return "minutes", normalized.removesuffix("min")
    if normalized.endswith("h"):
        return "hours", normalized.removesuffix("h")
    if normalized in {"1d", "day", "days"}:
        return "days", "1"
    raise ValueError(f"Unsupported timeframe for Upstox V3: {timeframe}")


def load_upstox_ohlc(
    client: UpstoxClient,
    instrument_key: str,
    timeframe: str,
    from_date: str,
    to_date: str,
) -> pd.DataFrame:
    """Fetch historical candles from Upstox V3 and return a sorted OHLC DataFrame."""
    unit, interval = timeframe_to_upstox_v3(timeframe)
    payload = client.historical_candles_v3(
        instrument_key=instrument_key,
        unit=unit,
        interval=interval,
        to_date=to_date,
        from_date=from_date,
    )
    candles = payload.get("data", {}).get("candles", [])
    if not candles:
        raise ValueError("Upstox returned no historical candles")
    frame = pd.DataFrame(
        candles,
        columns=["timestamp", "open", "high", "low", "close", "volume", "open_interest"],
    )
    frame["timestamp"] = pd.to_datetime(frame["timestamp"])
    numeric_columns = ["open", "high", "low", "close", "volume", "open_interest"]
    frame[numeric_columns] = frame[numeric_columns].apply(pd.to_numeric, errors="coerce")
    return frame.set_index("timestamp").sort_index()


def expired_interval_for_timeframe(timeframe: str) -> str:
    """Translate project timeframe aliases to expired-instrument API intervals."""
    normalized = timeframe.strip().lower()
    mapping = {
        "1min": "1minute",
        "3min": "3minute",
        "5min": "5minute",
        "15min": "15minute",
        "30min": "30minute",
        "1d": "day",
    }
    if normalized not in mapping:
        raise ValueError(f"Unsupported expired-instrument timeframe: {timeframe}")
    return mapping[normalized]


def candles_payload_to_frame(candles: list[list[object]]) -> pd.DataFrame:
    """Normalize Upstox candle arrays into a sorted OHLC frame."""
    if not candles:
        return pd.DataFrame(columns=["open", "high", "low", "close", "volume", "open_interest"])
    frame = pd.DataFrame(candles, columns=["timestamp", "open", "high", "low", "close", "volume", "open_interest"])
    frame["timestamp"] = pd.to_datetime(frame["timestamp"])
    numeric_columns = ["open", "high", "low", "close", "volume", "open_interest"]
    frame[numeric_columns] = frame[numeric_columns].apply(pd.to_numeric, errors="coerce")
    return frame.set_index("timestamp").sort_index()


def load_expired_upstox_ohlc(
    client: UpstoxClient,
    expired_instrument_key: str,
    timeframe: str,
    from_date: str,
    to_date: str,
) -> pd.DataFrame:
    """Fetch expired option/future candles from Upstox and return OHLC data."""
    payload = client.expired_historical_candles(
        expired_instrument_key=expired_instrument_key,
        interval=expired_interval_for_timeframe(timeframe),
        to_date=to_date,
        from_date=from_date,
    )
    return candles_payload_to_frame(payload.get("data", {}).get("candles", []))
