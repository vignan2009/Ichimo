from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from ichimoku_framework.strategy.models import Trade


def build_dashboard(candles: pd.DataFrame, trades: list[Trade], equity_curve: pd.Series) -> go.Figure:
    """Build an interactive research dashboard."""
    drawdown = equity_curve / equity_curve.cummax() - 1
    monthly = equity_curve.resample("ME").last().pct_change().dropna()
    fig = make_subplots(rows=3, cols=1, shared_xaxes=True, row_heights=[0.5, 0.25, 0.25])
    fig.add_trace(
        go.Candlestick(
            x=candles.index,
            open=candles["open"],
            high=candles["high"],
            low=candles["low"],
            close=candles["close"],
            name="Price",
        ),
        row=1,
        col=1,
    )
    for trade in trades:
        fig.add_trace(
            go.Scatter(
                x=[trade.entry_time, trade.exit_time],
                y=[trade.entry_price, trade.exit_price],
                mode="markers+lines",
                marker={"size": 8},
                name=f"{trade.side.value}:{trade.reason.value}",
                showlegend=False,
            ),
            row=1,
            col=1,
        )
    fig.add_trace(go.Scatter(x=equity_curve.index, y=equity_curve, name="Equity"), row=2, col=1)
    fig.add_trace(go.Scatter(x=drawdown.index, y=drawdown, name="Drawdown"), row=3, col=1)
    fig.update_layout(title="Ichimoku Strategy Dashboard", xaxis_rangeslider_visible=False)
    fig.add_annotation(
        text=f"Monthly samples: {len(monthly)}",
        xref="paper",
        yref="paper",
        x=1,
        y=0,
        showarrow=False,
    )
    return fig

