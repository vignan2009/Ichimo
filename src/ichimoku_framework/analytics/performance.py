from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from ichimoku_framework.strategy.models import Trade


@dataclass(frozen=True, slots=True)
class PerformanceSummary:
    net_pnl: float
    net_pnl_percent: float
    win_rate: float
    sharpe_ratio: float
    max_drawdown: float
    profit_factor: float
    avg_trade_duration_minutes: float
    median_trade: float
    mode_trade: float
    min_trade: float
    max_trade: float
    std_dev: float
    avg_bars_per_trade: float
    median_bars: float
    mode_bars: float
    min_bars: float
    max_bars: float
    std_dev_bars: float
    trade_distribution: dict[str, int]


def summarize(trades: list[Trade], equity_curve: pd.Series) -> PerformanceSummary:
    pnl = pd.Series([trade.pnl for trade in trades], dtype=float)
    pnl_percent = pd.Series([trade.pnl_percent for trade in trades], dtype=float)
    bars = pd.Series([trade.bars_held for trade in trades], dtype=float)
    returns = equity_curve.pct_change().dropna()
    winners = pnl[pnl > 0]
    losers = pnl[pnl < 0]
    durations = pd.Series([(trade.exit_time - trade.entry_time).total_seconds() / 60 for trade in trades], dtype=float)
    drawdown = equity_curve / equity_curve.cummax() - 1
    sharpe = 0.0 if returns.std(ddof=0) == 0 or returns.empty else float(np.sqrt(252) * returns.mean() / returns.std(ddof=0))
    profit_factor = float("inf") if losers.empty and not winners.empty else float(winners.sum() / abs(losers.sum())) if not losers.empty else 0.0
    return PerformanceSummary(
        net_pnl=float(pnl.sum()) if not pnl.empty else 0.0,
        net_pnl_percent=float(pnl_percent.sum()) if not pnl_percent.empty else 0.0,
        win_rate=float((pnl > 0).mean()) if not pnl.empty else 0.0,
        sharpe_ratio=sharpe,
        max_drawdown=float(drawdown.min()) if not drawdown.empty else 0.0,
        profit_factor=profit_factor,
        avg_trade_duration_minutes=float(durations.mean()) if not durations.empty else 0.0,
        median_trade=float(pnl_percent.median()) if not pnl_percent.empty else 0.0,
        mode_trade=float(pnl_percent.mode().iloc[0]) if not pnl_percent.empty else 0.0,
        min_trade=float(pnl_percent.min()) if not pnl_percent.empty else 0.0,
        max_trade=float(pnl_percent.max()) if not pnl_percent.empty else 0.0,
        std_dev=float(pnl_percent.std(ddof=0)) if not pnl_percent.empty else 0.0,
        avg_bars_per_trade=float(bars.mean()) if not bars.empty else 0.0,
        median_bars=float(bars.median()) if not bars.empty else 0.0,
        mode_bars=float(bars.mode().iloc[0]) if not bars.empty else 0.0,
        min_bars=float(bars.min()) if not bars.empty else 0.0,
        max_bars=float(bars.max()) if not bars.empty else 0.0,
        std_dev_bars=float(bars.std(ddof=0)) if not bars.empty else 0.0,
        trade_distribution={
            "wins": int((pnl > 0).sum()),
            "losses": int((pnl < 0).sum()),
            "breakeven": int((pnl == 0).sum()),
        },
    )
