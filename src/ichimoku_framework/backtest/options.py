from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

import pandas as pd

from ichimoku_framework.backtest.engine import BacktestEngine, BacktestResult
from ichimoku_framework.config.models import AppConfig
from ichimoku_framework.data.loaders import load_expired_upstox_ohlc
from ichimoku_framework.execution.options import OptionContract, contracts_from_payload, nearest_atm_contract, premium_fill_price
from ichimoku_framework.execution.upstox_client import UpstoxClient
from ichimoku_framework.strategy.logic import EntryDirection, close_decision, directional_entry
from ichimoku_framework.strategy.models import ExitReason, Position, Side, Trade
from ichimoku_framework.strategy.risk import stop_and_target
from ichimoku_framework.strategy.state_machine import TradeState


@dataclass(slots=True)
class PendingOptionEntry:
    signal_time: pd.Timestamp
    direction: EntryDirection
    delay_remaining: int


class OvernightOptionBacktestEngine(BacktestEngine):
    """Backtest long ATM options with overnight holds using premium OHLC data."""

    def __init__(self, config: AppConfig, client: UpstoxClient) -> None:
        super().__init__(config.strategy, config.backtest)
        self.app_config = config
        self.client = client
        self._expiries: list[date] | None = None
        self._contracts_by_expiry: dict[date, list[OptionContract]] = {}
        self._premium_by_contract: dict[str, pd.DataFrame] = {}

    def run(self, candles: pd.DataFrame) -> BacktestResult:
        frame = self.prepare(candles)
        state = TradeState(self.strategy_config)
        equity_values: list[float] = []
        pending: PendingOptionEntry | None = None
        bars_in_trade = 0
        previous_timestamp: pd.Timestamp | None = None
        previous_row: pd.Series | None = None
        previous_date: date | None = None

        for bar_index, (timestamp, row) in enumerate(frame.iterrows()):
            current_date = timestamp.date()
            if (
                not self.app_config.options.allow_overnight
                and previous_date is not None
                and current_date != previous_date
                and state.position is not None
                and previous_timestamp is not None
                and previous_row is not None
            ):
                premium_row = self._premium_row(state.position, previous_timestamp)
                if premium_row is not None:
                    self._close_position(
                        timestamp=previous_timestamp,
                        underlying_row=previous_row,
                        premium_exit=float(premium_row["close"]),
                        state=state,
                        bars_in_trade=bars_in_trade,
                        reason=ExitReason.END_OF_DAY,
                        exit_basis="session_end",
                    )
                    bars_in_trade = 0

            if pending is not None and state.position is None:
                pending.delay_remaining -= 1
                if pending.delay_remaining <= 0:
                    opened = self._open_option_position(timestamp, row, state, pending, bar_index)
                    if opened:
                        bars_in_trade = 1
                    pending = None

            if state.position is not None:
                if not (bars_in_trade == 1 and state.position.entry_bar_index == bar_index):
                    bars_in_trade += 1
                self._process_option_exit(timestamp, row, state, bars_in_trade)
                if state.position is None:
                    bars_in_trade = 0

            if state.position is None and pending is None and self._in_time_window(timestamp) and self._in_session(timestamp) and state.can_open(timestamp.date()):
                direction = directional_entry(row, self.strategy_config)
                if direction is not None:
                    pending = PendingOptionEntry(
                        signal_time=timestamp,
                        direction=direction,
                        delay_remaining=max(int(self.backtest_config.realistic_entry_delay_candles), 0),
                    )
                    if pending.delay_remaining == 0:
                        opened = self._open_option_position(timestamp, row, state, pending, bar_index)
                        if opened:
                            bars_in_trade = 1
                        pending = None

            equity_values.append(self._equity(state, timestamp))
            previous_timestamp, previous_row, previous_date = timestamp, row, current_date

        if state.position is not None:
            last_timestamp = frame.index[-1]
            last_row = frame.iloc[-1]
            premium_row = self._premium_row(state.position, last_timestamp)
            if premium_row is not None:
                self._close_position(
                    timestamp=last_timestamp,
                    underlying_row=last_row,
                    premium_exit=float(premium_row["close"]),
                    state=state,
                    bars_in_trade=bars_in_trade,
                    reason=ExitReason.END_OF_DAY,
                    exit_basis="end_of_backtest",
                )

        return BacktestResult(frame, state.trades, pd.Series(equity_values, index=frame.index, name="equity"))

    def _open_option_position(
        self,
        timestamp: pd.Timestamp,
        underlying_row: pd.Series,
        state: TradeState,
        pending: PendingOptionEntry,
        bar_index: int,
    ) -> bool:
        expiry = self._nearest_expiry(timestamp.date())
        contract = nearest_atm_contract(
            self._contracts(expiry),
            spot_price=float(underlying_row["open"]),
            bullish=pending.direction == EntryDirection.BULLISH,
            expiry=expiry,
        )
        premium_row = self._premium_row_for_contract(contract, timestamp)
        if premium_row is None:
            return False
        raw_premium = float(premium_row["open"])
        entry_price = premium_fill_price(raw_premium, bullish=True, slippage_bps=self.app_config.options.slippage_bps)
        stop_loss, take_profit = stop_and_target(entry_price, premium_row, self.strategy_config)
        state.position = Position(
            side=Side.LONG,
            entry_time=timestamp.to_pydatetime(),
            entry_price=entry_price,
            quantity=contract.lot_size * self.app_config.options.lots,
            stop_loss=stop_loss,
            take_profit=take_profit,
            signal_time=pending.signal_time.to_pydatetime(),
            raw_entry_price=raw_premium,
            entry_bar_index=bar_index,
            instrument_key=contract.instrument_key,
            trading_symbol=contract.trading_symbol,
            option_type=contract.option_type,
            strike_price=contract.strike_price,
            expiry=datetime.combine(contract.expiry, datetime.min.time()),
            underlying_entry_price=float(underlying_row["open"]),
        )
        return True

    def _process_option_exit(self, timestamp: pd.Timestamp, underlying_row: pd.Series, state: TradeState, bars_in_trade: int) -> None:
        position = state.position
        if position is None:
            return
        premium_row = self._premium_row(position, timestamp)
        if premium_row is None:
            return
        if position.expiry is not None and timestamp.date() >= position.expiry.date():
            self._close_position(timestamp, underlying_row, float(premium_row["close"]), state, bars_in_trade, ExitReason.END_OF_DAY, "contract_expiry")
            return
        hit_stop = position.stop_loss is not None and float(premium_row["low"]) <= position.stop_loss
        hit_target = position.take_profit is not None and float(premium_row["high"]) >= position.take_profit
        if hit_stop:
            self._close_position(timestamp, underlying_row, float(position.stop_loss), state, bars_in_trade, ExitReason.STOP_LOSS, "premium_bar_touch")
        elif hit_target:
            self._close_position(timestamp, underlying_row, float(position.take_profit), state, bars_in_trade, ExitReason.TAKE_PROFIT, "premium_bar_touch")
        elif close_decision(underlying_row, self.strategy_config).triggered:
            exit_price = float(premium_row["close"]) * (1 - self.app_config.options.slippage_bps / 10000.0)
            self._close_position(timestamp, underlying_row, exit_price, state, bars_in_trade, ExitReason.CLOSE_SIGNAL, "underlying_close_signal")

    def _close_position(
        self,
        timestamp: pd.Timestamp,
        underlying_row: pd.Series,
        premium_exit: float,
        state: TradeState,
        bars_in_trade: int,
        reason: ExitReason,
        exit_basis: str,
    ) -> None:
        position = state.position
        if position is None:
            return
        gross_pnl = (premium_exit - position.entry_price) * position.quantity
        costs = self.backtest_config.commission_per_order * 2
        state.close(
            Trade(
                side=position.side,
                entry_time=position.entry_time,
                exit_time=timestamp.to_pydatetime(),
                entry_price=position.entry_price,
                exit_price=premium_exit,
                quantity=position.quantity,
                pnl=gross_pnl - costs,
                pnl_percent=(premium_exit - position.entry_price) / position.entry_price * 100.0,
                bars_held=bars_in_trade,
                reason=reason,
                signal_time=position.signal_time,
                raw_entry_price=position.raw_entry_price,
                gross_pnl=gross_pnl,
                costs=costs,
                exit_basis=exit_basis,
                instrument_key=position.instrument_key,
                trading_symbol=position.trading_symbol,
                option_type=position.option_type,
                strike_price=position.strike_price,
                expiry=position.expiry,
                underlying_entry_price=position.underlying_entry_price,
                underlying_exit_price=float(underlying_row["close"]),
            )
        )

    def _nearest_expiry(self, entry_date: date) -> date:
        expiries = [expiry for expiry in self._load_expiries() if expiry >= entry_date]
        if not expiries:
            raise ValueError(f"No eligible expiry on or after {entry_date}")
        return min(expiries)

    def _load_expiries(self) -> list[date]:
        if self._expiries is None:
            payload = self.client.expired_expiries(self.app_config.data.instrument_key)
            values = payload.get("data", [])
            self._expiries = sorted(datetime.strptime(str(value), "%Y-%m-%d").date() for value in values)
        return self._expiries

    def _contracts(self, expiry: date) -> list[OptionContract]:
        if expiry not in self._contracts_by_expiry:
            payload = self.client.expired_option_contracts(self.app_config.data.instrument_key, expiry.isoformat())
            self._contracts_by_expiry[expiry] = contracts_from_payload(payload.get("data", []))
        return self._contracts_by_expiry[expiry]

    def _premium_row_for_contract(self, contract: OptionContract, timestamp: pd.Timestamp) -> pd.Series | None:
        premium = self._premium_frame(contract)
        if timestamp not in premium.index:
            return None
        return premium.loc[timestamp]

    def _premium_row(self, position: Position, timestamp: pd.Timestamp) -> pd.Series | None:
        if position.instrument_key is None or position.expiry is None:
            return None
        contract = OptionContract(
            instrument_key=position.instrument_key,
            expiry=position.expiry.date(),
            strike_price=float(position.strike_price or 0.0),
            option_type=str(position.option_type),
            lot_size=max(position.quantity // max(self.app_config.options.lots, 1), 1),
            trading_symbol=position.trading_symbol,
        )
        return self._premium_row_for_contract(contract, timestamp)

    def _premium_frame(self, contract: OptionContract) -> pd.DataFrame:
        if contract.instrument_key not in self._premium_by_contract:
            end_date = min(contract.expiry.isoformat(), self.app_config.data.to_date)
            self._premium_by_contract[contract.instrument_key] = load_expired_upstox_ohlc(
                self.client,
                expired_instrument_key=contract.instrument_key,
                timeframe=self.app_config.data.timeframe,
                from_date=self.app_config.data.from_date,
                to_date=end_date,
            )
        return self._premium_by_contract[contract.instrument_key]

    def _equity(self, state: TradeState, timestamp: pd.Timestamp) -> float:
        realized = sum(trade.pnl for trade in state.trades)
        position = state.position
        if position is None:
            return self.backtest_config.initial_capital + realized
        premium_row = self._premium_row(position, timestamp)
        unrealized = 0.0 if premium_row is None else (float(premium_row["close"]) - position.entry_price) * position.quantity
        return self.backtest_config.initial_capital + realized + unrealized
