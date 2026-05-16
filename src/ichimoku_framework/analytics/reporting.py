from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any

import pandas as pd

from ichimoku_framework.analytics.performance import PerformanceSummary
from ichimoku_framework.backtest.engine import BacktestResult
from ichimoku_framework.config.models import AppConfig
from ichimoku_framework.strategy.models import Trade

REPORT_TIMEZONE = "Asia/Kolkata"


def trades_to_frame(trades: list[Trade], mode: str) -> pd.DataFrame:
    """Convert trade objects into a flat ledger suitable for export."""
    rows: list[dict[str, Any]] = []
    for trade in trades:
        row = asdict(trade)
        row["mode"] = mode
        row["side"] = trade.side.value
        row["reason"] = trade.reason.value
        rows.append(row)
    return excel_safe_frame(pd.DataFrame(rows))


def summary_to_frame(
    pine_summary: PerformanceSummary,
    realistic_summary: PerformanceSummary,
    option_summary: PerformanceSummary | None = None,
) -> pd.DataFrame:
    """Return a comparison table for the configured execution modes."""
    rows = []
    summaries: list[tuple[str, PerformanceSummary]] = [
        ("pine_exact", pine_summary),
        ("realistic", realistic_summary),
    ]
    if option_summary is not None:
        summaries.append(("overnight_options", option_summary))
    for mode, summary in summaries:
        row = asdict(summary)
        row["mode"] = mode
        distribution = row.pop("trade_distribution")
        row.update(distribution)
        rows.append(row)
    return pd.DataFrame(rows).set_index("mode").reset_index()


def equity_to_frame(
    pine_result: BacktestResult,
    realistic_result: BacktestResult,
    option_result: BacktestResult | None = None,
) -> pd.DataFrame:
    """Align available equity curves by timestamp for export."""
    curves = [
        pine_result.equity_curve.rename("pine_exact_equity"),
        realistic_result.equity_curve.rename("realistic_equity"),
    ]
    if option_result is not None:
        curves.append(option_result.equity_curve.rename("overnight_options_equity"))
    frame = pd.concat(curves, axis=1).reset_index(names="timestamp")
    return excel_safe_frame(frame)


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
        return pd.DataFrame(columns=["month", "pine_exact_return", "realistic_return", "overnight_options_return"])
    frame = equity.copy()
    frame["timestamp"] = pd.to_datetime(frame["timestamp"])
    equity_columns = [column for column in frame.columns if column.endswith("_equity")]
    monthly = frame.set_index("timestamp")[equity_columns].resample("ME").last().pct_change().dropna(how="all")
    monthly = monthly.rename(columns={column: column.replace("_equity", "_return") for column in equity_columns})
    return monthly.reset_index(names="month")


def excel_safe_frame(frame: pd.DataFrame) -> pd.DataFrame:
    """Return an Excel-compatible copy with timezone-aware values shown in IST."""
    safe = frame.copy()
    for column in safe.columns:
        series = safe[column]
        if isinstance(series.dtype, pd.DatetimeTZDtype):
            safe[column] = series.dt.tz_convert(REPORT_TIMEZONE).dt.tz_localize(None)
        elif series.dtype == "object":
            safe[column] = series.map(_excel_safe_value)
    return safe


def _excel_safe_value(value: Any) -> Any:
    if isinstance(value, pd.Timestamp) and value.tzinfo is not None:
        return value.tz_convert(REPORT_TIMEZONE).tz_localize(None)
    if hasattr(value, "tzinfo") and getattr(value, "tzinfo", None) is not None:
        return pd.Timestamp(value).tz_convert(REPORT_TIMEZONE).tz_localize(None).to_pydatetime()
    return value


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
    option_result: BacktestResult | None = None,
    option_summary: PerformanceSummary | None = None,
) -> Path:
    """Write a multi-sheet Excel report for a complete backtest run."""
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)

    pine_trades = trades_to_frame(pine_result.trades, "pine_exact")
    realistic_trades = trades_to_frame(realistic_result.trades, "realistic")
    option_trades = trades_to_frame(option_result.trades, "overnight_options") if option_result is not None else pd.DataFrame()
    all_trades = pd.concat([pine_trades, realistic_trades, option_trades], ignore_index=True)
    equity = equity_to_frame(pine_result, realistic_result, option_result)

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        excel_safe_frame(summary_to_frame(pine_summary, realistic_summary, option_summary)).to_excel(writer, sheet_name="Summary", index=False)
        excel_safe_frame(pine_trades).to_excel(writer, sheet_name="Trades_PineExact", index=False)
        excel_safe_frame(realistic_trades).to_excel(writer, sheet_name="Trades_Realistic", index=False)
        if option_result is not None:
            excel_safe_frame(option_trades).to_excel(writer, sheet_name="Trades_OvernightOptions", index=False)
        excel_safe_frame(daily_pnl_frame(all_trades)).to_excel(writer, sheet_name="Daily_PnL", index=False)
        excel_safe_frame(monthly_returns_frame(equity)).to_excel(writer, sheet_name="Monthly_Returns", index=False)
        excel_safe_frame(equity).to_excel(writer, sheet_name="Equity_Curves", index=False)
        excel_safe_frame(config_to_frame(config)).to_excel(writer, sheet_name="Config", index=False)

    return output
