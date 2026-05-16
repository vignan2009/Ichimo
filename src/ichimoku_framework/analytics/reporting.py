from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any

import pandas as pd

from ichimoku_framework.analytics.performance import PerformanceSummary
from ichimoku_framework.backtest.engine import BacktestResult
from ichimoku_framework.config.models import AppConfig
from ichimoku_framework.strategy.models import Trade


def trades_to_frame(trades: list[Trade], mode: str) -> pd.DataFrame:
    """Convert trade objects into a flat ledger suitable for export."""
    rows: list[dict[str, Any]] = []
    for trade in trades:
        row = asdict(trade)
        row["mode"] = mode
        row["side"] = trade.side.value
        row["reason"] = trade.reason.value
        rows.append(row)
    return pd.DataFrame(rows)


def summary_to_frame(pine_summary: PerformanceSummary, realistic_summary: PerformanceSummary) -> pd.DataFrame:
    """Return a two-row comparison table for the two execution modes."""
    rows = []
    for mode, summary in (("pine_exact", pine_summary), ("realistic", realistic_summary)):
        row = asdict(summary)
        row["mode"] = mode
        distribution = row.pop("trade_distribution")
        row.update(distribution)
        rows.append(row)
    return pd.DataFrame(rows).set_index("mode").reset_index()


def equity_to_frame(pine_result: BacktestResult, realistic_result: BacktestResult) -> pd.DataFrame:
    """Align both equity curves by timestamp for export."""
    return pd.concat(
        [
            pine_result.equity_curve.rename("pine_exact_equity"),
            realistic_result.equity_curve.rename("realistic_equity"),
        ],
        axis=1,
    ).reset_index(names="timestamp")


def daily_pnl_frame(trades: pd.DataFrame) -> pd.DataFrame:
    """Aggregate daily realized PnL by execution mode."""
    if trades.empty:
        return pd.DataFrame(columns=["mode", "date", "pnl"])
    frame = trades.copy()
    frame["date"] = pd.to_datetime(frame["exit_time"]).dt.date
    return frame.groupby(["mode", "date"], as_index=False)["pnl"].sum()


def monthly_returns_frame(equity: pd.DataFrame) -> pd.DataFrame:
    """Compute monthly equity returns for each execution mode."""
    if equity.empty:
        return pd.DataFrame(columns=["month", "pine_exact_return", "realistic_return"])
    frame = equity.copy()
    frame["timestamp"] = pd.to_datetime(frame["timestamp"])
    monthly = frame.set_index("timestamp")[["pine_exact_equity", "realistic_equity"]].resample("ME").last().pct_change().dropna(how="all")
    monthly = monthly.rename(
        columns={
            "pine_exact_equity": "pine_exact_return",
            "realistic_equity": "realistic_return",
        }
    )
    return monthly.reset_index(names="month")


def config_to_frame(config: AppConfig) -> pd.DataFrame:
    """Flatten the Pydantic config into key/value rows."""
    flattened: dict[str, Any] = {}

    def walk(prefix: str, value: Any) -> None:
        if isinstance(value, dict):
            for key, nested in value.items():
                walk(f"{prefix}.{key}" if prefix else key, nested)
        else:
            flattened[prefix] = value

    walk("", config.model_dump(mode="json"))
    return pd.DataFrame({"key": list(flattened.keys()), "value": list(flattened.values())})


def export_excel_report(
    path: str | Path,
    config: AppConfig,
    pine_result: BacktestResult,
    realistic_result: BacktestResult,
    pine_summary: PerformanceSummary,
    realistic_summary: PerformanceSummary,
) -> Path:
    """Write a multi-sheet Excel report for a complete backtest run."""
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)

    pine_trades = trades_to_frame(pine_result.trades, "pine_exact")
    realistic_trades = trades_to_frame(realistic_result.trades, "realistic")
    all_trades = pd.concat([pine_trades, realistic_trades], ignore_index=True)
    equity = equity_to_frame(pine_result, realistic_result)

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        summary_to_frame(pine_summary, realistic_summary).to_excel(writer, sheet_name="Summary", index=False)
        pine_trades.to_excel(writer, sheet_name="Trades_PineExact", index=False)
        realistic_trades.to_excel(writer, sheet_name="Trades_Realistic", index=False)
        daily_pnl_frame(all_trades).to_excel(writer, sheet_name="Daily_PnL", index=False)
        monthly_returns_frame(equity).to_excel(writer, sheet_name="Monthly_Returns", index=False)
        equity.to_excel(writer, sheet_name="Equity_Curves", index=False)
        config_to_frame(config).to_excel(writer, sheet_name="Config", index=False)

    return output
