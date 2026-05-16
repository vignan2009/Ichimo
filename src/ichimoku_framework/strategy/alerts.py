from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True, slots=True)
class AlertEvent:
    name: str
    message: str


def alert_events(row: pd.Series) -> list[AlertEvent]:
    """Emit strategy alerts mirroring the boolean signal surface."""
    events: list[AlertEvent] = []
    if bool(row.get("bullish_cross", False)):
        events.append(AlertEvent("bullish_cross", f"Bullish {row.get('bullish_class', 'unknown')} cross"))
    if bool(row.get("bearish_cross", False)):
        events.append(AlertEvent("bearish_cross", f"Bearish {row.get('bearish_class', 'unknown')} cross"))
    return events

