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
