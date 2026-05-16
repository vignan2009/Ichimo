from __future__ import annotations

import pandas as pd

from ichimoku_framework.analytics.reporting import excel_safe_frame, monthly_returns_frame, trades_to_frame
from ichimoku_framework.strategy.models import ExitReason, Side, Trade


def test_trades_to_frame_flattens_enums() -> None:
    trade = Trade(
        side=Side.LONG,
        entry_time=pd.Timestamp("2024-01-01 09:15").to_pydatetime(),
        exit_time=pd.Timestamp("2024-01-01 09:30").to_pydatetime(),
        entry_price=100.0,
        exit_price=101.0,
        quantity=1,
        pnl=1.0,
        pnl_percent=1.0,
        bars_held=1,
        reason=ExitReason.TAKE_PROFIT,
    )
    frame = trades_to_frame([trade], "realistic")
    assert frame.loc[0, "side"] == "long"
    assert frame.loc[0, "reason"] == "take_profit"


def test_monthly_returns_frame_handles_two_months() -> None:
    equity = pd.DataFrame(
        {
            "timestamp": pd.to_datetime(["2024-01-31", "2024-02-29"]),
            "pine_exact_equity": [100.0, 110.0],
            "realistic_equity": [100.0, 90.0],
        }
    )
    frame = monthly_returns_frame(equity)
    assert round(frame.loc[0, "pine_exact_return"], 4) == 0.1
    assert round(frame.loc[0, "realistic_return"], 4) == -0.1


def test_excel_safe_frame_converts_timezone_aware_values_to_ist() -> None:
    frame = pd.DataFrame({"timestamp": pd.to_datetime(["2024-01-01 09:15"], utc=True)})
    safe = excel_safe_frame(frame)
    assert safe["timestamp"].dt.tz is None
    assert safe.loc[0, "timestamp"] == pd.Timestamp("2024-01-01 14:45")
