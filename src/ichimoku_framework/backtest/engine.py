from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from ichimoku_framework.config.models import BacktestConfig, StrategyConfig
from ichimoku_framework.indicators.ichimoku import average_true_range, ichimoku
from ichimoku_framework.indicators.signals import classify_crosses
from ichimoku_framework.strategy.logic import close_decision, entry_decision
from ichimoku_framework.strategy.models import ExitReason, Position, Side, Trade
from ichimoku_framework.strategy.risk import stop_and_target
from ichimoku_framework.strategy.state_machine import TradeState


@dataclass(slots=True)
class BacktestResult:
    candles: pd.DataFrame
    trades: list[Trade]
    equity_curve: pd.Series


class BacktestEngine:
    """Single-position, candle-by-candle execution engine."""

    def __init__(self, strategy_config: StrategyConfig, backtest_config: BacktestConfig) -> None:
        self.strategy_config = strategy_config
        self.backtest_config = backtest_config

    def prepare(self, candles: pd.DataFrame) -> pd.DataFrame:
        required = {"open", "high", "low", "close"}
        missing = required.difference(candles.columns)
        if missing:
            raise ValueError(f"Missing OHLC columns: {sorted(missing)}")
        frame = candles.sort_index().copy()
        entry_frame = ichimoku(
            frame,
            self.strategy_config.entry_tenkan_period,
            self.strategy_config.entry_kijun_period,
            self.strategy_config.entry_senkou_b_period,
            self.strategy_config.entry_displacement,
        ).rename(
            columns={
                "tenkan": "entry_tenkan",
                "kijun": "entry_kijun",
                "senkou_a_raw": "entry_senkou_a_raw",
                "senkou_b_raw": "entry_senkou_b_raw",
                "senkou_a": "entry_senkou_a",
                "senkou_b": "entry_senkou_b",
                "chikou": "entry_chikou",
            }
        )
        close_frame = ichimoku(
            frame,
            self.strategy_config.close_tenkan_period,
            self.strategy_config.close_kijun_period,
            self.strategy_config.close_senkou_b_period,
            self.strategy_config.close_displacement,
        ).rename(
            columns={
                "tenkan": "close_tenkan",
                "kijun": "close_kijun",
                "senkou_a_raw": "close_senkou_a_raw",
                "senkou_b_raw": "close_senkou_b_raw",
                "senkou_a": "close_senkou_a",
                "senkou_b": "close_senkou_b",
                "chikou": "close_chikou",
            }
        )
        frame = entry_frame.join(
            close_frame[
                [
                    "close_tenkan",
                    "close_kijun",
                    "close_senkou_a_raw",
                    "close_senkou_b_raw",
                    "close_senkou_a",
                    "close_senkou_b",
                    "close_chikou",
                ]
            ]
        )
        frame["atr"] = average_true_range(frame, self.strategy_config.atr_period)
        frame = classify_crosses(frame, "entry_")
        return classify_crosses(frame, "close_")

    def run(self, candles: pd.DataFrame) -> BacktestResult:
        frame = self.prepare(candles)
        state = TradeState(self.strategy_config)
        equity_values: list[float] = []
        cash = self.backtest_config.initial_capital
        bars_in_trade = 0

        for timestamp, row in frame.iterrows():
            if state.position is not None and self._in_time_window(timestamp):
                bars_in_trade += 1
            exited = self._process_exit(timestamp, row, state, bars_in_trade)
            if exited:
                bars_in_trade = 0
            if state.position is None and self._in_time_window(timestamp) and self._in_session(timestamp) and state.can_open(timestamp.date()):
                decision = entry_decision(row, self.strategy_config)
                if decision.triggered:
                    fill_price = self._apply_entry_slippage(float(row["close"]), Side.LONG)
                    stop_loss, take_profit = stop_and_target(fill_price, row, self.strategy_config)
                    state.position = Position(
                        side=Side.LONG,
                        entry_time=timestamp.to_pydatetime(),
                        entry_price=fill_price,
                        quantity=self.backtest_config.quantity,
                        stop_loss=stop_loss,
                        take_profit=take_profit,
                    )
                    cash -= self.backtest_config.commission_per_order
                    bars_in_trade = 1
            unrealized = self._unrealized_pnl(state.position, float(row["close"]))
            equity_values.append(cash + sum(trade.pnl for trade in state.trades) + unrealized)

        return BacktestResult(frame, state.trades, pd.Series(equity_values, index=frame.index, name="equity"))

    def _process_exit(self, timestamp: pd.Timestamp, row: pd.Series, state: TradeState, bars_in_trade: int) -> bool:
        position = state.position
        if position is None:
            return False
        exit_price: float | None = None
        reason: ExitReason | None = None
        hit_stop = position.stop_loss is not None and float(row["low"]) <= position.stop_loss
        hit_target = position.take_profit is not None and float(row["high"]) >= position.take_profit

        if hit_stop:
            exit_price, reason = position.stop_loss, ExitReason.STOP_LOSS
        elif hit_target:
            exit_price, reason = position.take_profit, ExitReason.TAKE_PROFIT
        elif self._in_time_window(timestamp) and close_decision(row, self.strategy_config).triggered:
            exit_price, reason = self._apply_exit_slippage(float(row["close"]), position.side), ExitReason.CLOSE_SIGNAL

        if reason is None or exit_price is None:
            return False
        pnl = self._pnl(position, float(exit_price)) - self.backtest_config.commission_per_order
        pnl_percent = (float(exit_price) - position.entry_price) / position.entry_price * 100.0
        state.close(
            Trade(
                side=position.side,
                entry_time=position.entry_time,
                exit_time=timestamp.to_pydatetime(),
                entry_price=position.entry_price,
                exit_price=float(exit_price),
                quantity=position.quantity,
                pnl=pnl,
                pnl_percent=pnl_percent,
                bars_held=bars_in_trade,
                reason=reason,
            )
        )
        return True

    def _apply_entry_slippage(self, price: float, side: Side) -> float:
        factor = self.backtest_config.slippage_bps / 10000.0
        return price * (1 + factor if side == Side.LONG else 1 - factor)

    def _apply_exit_slippage(self, price: float, side: Side) -> float:
        factor = self.backtest_config.slippage_bps / 10000.0
        return price * (1 - factor if side == Side.LONG else 1 + factor)

    @staticmethod
    def _pnl(position: Position, exit_price: float) -> float:
        delta = exit_price - position.entry_price
        return delta * position.quantity if position.side == Side.LONG else -delta * position.quantity

    def _unrealized_pnl(self, position: Position | None, mark_price: float) -> float:
        return 0.0 if position is None else self._pnl(position, mark_price)

    def _in_session(self, timestamp: pd.Timestamp) -> bool:
        session_time = timestamp.time()
        return self.strategy_config.session_start <= session_time <= self.strategy_config.session_end

    def _in_time_window(self, timestamp: pd.Timestamp) -> bool:
        plain = timestamp.to_pydatetime().replace(tzinfo=None)
        return self.strategy_config.start_datetime <= plain <= self.strategy_config.end_datetime
