from __future__ import annotations

from pathlib import Path

import pandas as pd


def load_ohlc_csv(path: str | Path) -> pd.DataFrame:
    """Load a CSV with timestamp/open/high/low/close columns."""
    frame = pd.read_csv(path, parse_dates=["timestamp"])
    return frame.set_index("timestamp").sort_index()

