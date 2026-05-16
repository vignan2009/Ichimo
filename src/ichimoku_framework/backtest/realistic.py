from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from ichimoku_framework.backtest.engine import BacktestEngine, BacktestResult
from ichimoku_framework.config.models import BacktestConfig, StrategyConfig
from ichimoku_framework.strategy.logic import close_decision, entry_decision
from ichimoku_framework.strategy.models import ExitReason, Position, Side, Trade
from ichimoku_framework.strategy.risk import stop_and_target
from ichimoku_framework.strategy.state_machine import TradeState


@dataclass(slots=True)
class PendingEntry:
    signal_time: pd.Timestamp
    delay_remaining: int


class RealisticBacktestEngine(BacktestEngine):
    """Execution-realistic engine using delayed next-open fills and EOD handling."""

    def run(self, candles: pd.DataFrame) -> BacktestResult:
        frame = self.prepare(candles)
        state = TradeState(self.strategy_config)
        equity_values: list[float] = []
        pending: PendingEntry | None = None
        previous_timestamp: pd.Timestamp | None = None
        previous_row: pd.Series | None = None
        previous_date = None
        bars_in_trade = 0

        for bar_index, (timestamp, row) in enumerate(frame.iterrows()):
            current_date = timestamp.date()
            current_time = timestamp.time()

            if previous_date is not None and current_date != previous_date:
                if state.position is not None and previous_timestamp is not None and previous_row is not None:
                    self._close_position(previous_timestamp, previous_row, state, bars_in_trade, ExitReason.END_OF_DAY, float(previous_row["close"]), "same_day_last_available")
                    bars_in_trade = 0
                pending = None

            if current_time < self.strategy_config.session_start or current_time >= self.backtest_config.realistic_eod_time:
                if state.position is not None:
                    basis_timestamp = previous_timestamp if previous_timestamp is not None and previous_timestamp.date() == current_date else timestamp
                    basis_row = previous_row if previous_timestamp is not None and previous_timestamp.date() == current_date else row
                    self._close_position(basis_timestamp, basis_row, state, bars_in_trade, ExitReason.END_OF_DAY, float(basis_row["close"]), "same_day_last_available")
                    bars_in_trade = 0
                pending = None
                equity_values.append(self._equity(state, float(row["close"])))
                previous_timestamp, previous_row, previous_date = timestamp, row, current_date
                continue

            if pending is not None and state.position is None:
                pending.delay_remaining -= 1
                if pending.delay_remaining <= 0:
                    if current_time < self.backtest_config.realistic_no_entry_after and self._in_time_window(timestamp) and state.can_open(current_date):
                        self._open_position(timestamp, row, state, pending.signal_time, bar_index)
                        bars_in_trade = 1
                    pending = None

            if state.position is not None:
                if not (bars_in_trade == 1 and state.position.entry_bar_index == bar_index):
                    bars_in_trade += 1
                self._process_realistic_exit(timestamp, row, state, bars_in_trade, bar_index)
                if state.position is None:
                    bars_in_trade = 0

            if state.position is None and pending is None and current_time < self.backtest_config.realistic_no_entry_after and self._in_time_window(timestamp) and self._in_session(timestamp) and state.can_open(current_date) and entry_decision(row, self.strategy_config).triggered:
                delay = max(int(self.backtest_config.realistic_entry_delay_candles), 0)
                if delay == 0:
                    self._open_position(timestamp, row, state, timestamp, bar_index)
                    bars_in_trade = 1
                else:
                    pending = PendingEntry(timestamp, delay)

            equity_values.append(self._equity(state, float(row["close"])))
            previous_timestamp, previous_row, previous_date = timestamp, row, current_date

        if state.position is not None and previous_timestamp is not None and previous_row is not None:
            self._close_position(previous_timestamp, previous_row, state, bars_in_trade, ExitReason.END_OF_DAY, float(previous_row["close"]), "same_day_last_available")

        return BacktestResult(frame, state.trades, pd.Series(equity_values, index=frame.index, name="equity"))

    def _open_position(self, timestamp: pd.Timestamp, row: pd.Series, state: TradeState, signal_time: pd.Timestamp, bar_index: int) -> None:
        fill_price = float(row["open"]) + self.backtest_config.realistic_entry_slippage_points
        stop_loss, take_profit = stop_and_target(fill_price, row, self.strategy_config)
        state.position = Position(
            side=Side.LONG,
            entry_time=timestamp.to_pydatetime(),
            entry_price=fill_price,
            quantity=self.backtest_config.quantity,
            stop_loss=stop_loss,
            take_profit=take_profit,
            signal_time=signal_time.to_pydatetime(),
            raw_entry_price=float(row["open"]),
            entry_bar_index=bar_index,
        )

    def _process_realistic_exit(self, timestamp: pd.Timestamp, row: pd.Series, state: TradeState, bars_in_trade: int, bar_index: int) -> None:
        position = state.position
        if position is None:
            return
        same_bar = position.entry_bar_index == bar_index
        hit_stop = position.stop_loss is not None and float(row["low"]) <= position.stop_loss
        hit_target = position.take_profit is not None and float(row["high"]) >= position.take_profit
        if hit_stop:
            self._close_position(timestamp, row, state, bars_in_trade, ExitReason.STOP_LOSS, float(position.stop_loss), "same_bar_proxy_close" if same_bar else "bar_touch")
        elif hit_target:
            self._close_position(timestamp, row, state, bars_in_trade, ExitReason.TAKE_PROFIT, float(position.take_profit), "same_bar_proxy_close" if same_bar else "bar_touch")
        elif close_decision(row, self.strategy_config).triggered:
            self._close_position(timestamp, row, state, bars_in_trade, ExitReason.CLOSE_SIGNAL, float(row["close"]) - self.backtest_config.realistic_exit_slippage_points, "close_signal")

    def _close_position(self, timestamp: pd.Timestamp, row: pd.Series, state: TradeState, bars_in_trade: int, reason: ExitReason, exit_price: float, exit_basis: str) -> None:
        position = state.position
        if position is None:
            return
        if reason == ExitReason.END_OF_DAY:
            exit_price -= self.backtest_config.realistic_exit_slippage_points
        gross_pnl = self._pnl(position, exit_price)
        costs = self.backtest_config.commission_per_order * 2
        pnl = gross_pnl - costs
        state.close(
            Trade(
                side=position.side,
                entry_time=position.entry_time,
                exit_time=timestamp.to_pydatetime(),
                entry_price=position.entry_price,
                exit_price=exit_price,
                quantity=position.quantity,
                pnl=pnl,
                pnl_percent=(exit_price - position.entry_price) / position.entry_price * 100.0,
                bars_held=bars_in_trade,
                reason=reason,
                signal_time=position.signal_time,
                raw_entry_price=position.raw_entry_price,
                gross_pnl=gross_pnl,
                costs=costs,
                exit_basis=exit_basis,
            )
        )

    def _equity(self, state: TradeState, mark_price: float) -> float:
        return self.backtest_config.initial_capital + sum(trade.pnl for trade in state.trades) + self._unrealized_pnl(state.position, mark_price)
