from __future__ import annotations

import pandas as pd

from ichimoku_framework.backtest.options import OvernightOptionBacktestEngine
from ichimoku_framework.config.models import AppConfig, DataConfig, StrategyConfig
from ichimoku_framework.execution.options import contracts_from_payload, nearest_atm_contract
from ichimoku_framework.strategy.logic import EntryDirection, directional_entry
from ichimoku_framework.strategy.models import ExitReason


def test_directional_entry_maps_bullish_and_bearish_classes() -> None:
    config = StrategyConfig()
    assert directional_entry(pd.Series({"entry_bullish_class": "strong", "entry_bearish_class": pd.NA}), config) == EntryDirection.BULLISH
    assert directional_entry(pd.Series({"entry_bullish_class": pd.NA, "entry_bearish_class": "strong"}), config) == EntryDirection.BEARISH


def test_contract_selection_chooses_atm_type() -> None:
    contracts = contracts_from_payload(
        [
            {"instrument_key": "ce-1", "expiry": "2026-04-16", "strike_price": 23950, "instrument_type": "CE", "lot_size": 75},
            {"instrument_key": "ce-2", "expiry": "2026-04-16", "strike_price": 24000, "instrument_type": "CE", "lot_size": 75},
            {"instrument_key": "pe-1", "expiry": "2026-04-16", "strike_price": 24000, "instrument_type": "PE", "lot_size": 75},
        ]
    )
    contract = nearest_atm_contract(contracts, spot_price=23992, bullish=True, expiry=pd.Timestamp("2026-04-16").date())
    assert contract.instrument_key == "ce-2"


class _FakeClient:
    def expired_expiries(self, instrument_key: str) -> dict[str, list[str]]:
        assert instrument_key == "NSE_INDEX|Nifty 50"
        return {"data": ["2026-04-16"]}

    def expired_option_contracts(self, instrument_key: str, expiry_date: str) -> dict[str, list[dict[str, object]]]:
        assert instrument_key == "NSE_INDEX|Nifty 50"
        assert expiry_date == "2026-04-16"
        return {
            "data": [
                {
                    "instrument_key": "ce-24000",
                    "expiry": "2026-04-16",
                    "strike_price": 24000,
                    "instrument_type": "CE",
                    "lot_size": 75,
                    "trading_symbol": "NIFTY26APR24000CE",
                },
                {
                    "instrument_key": "pe-24000",
                    "expiry": "2026-04-16",
                    "strike_price": 24000,
                    "instrument_type": "PE",
                    "lot_size": 75,
                    "trading_symbol": "NIFTY26APR24000PE",
                },
            ]
        }


def _prepared_frame(direction: EntryDirection) -> pd.DataFrame:
    index = pd.date_range("2026-04-13 09:15", periods=3, freq="15min")
    frame = pd.DataFrame(
        {
            "open": [23992.0, 24001.0, 24010.0],
            "high": [24000.0, 24010.0, 24020.0],
            "low": [23980.0, 23990.0, 24000.0],
            "close": [23995.0, 24005.0, 24015.0],
            "entry_bullish_class": [pd.NA, pd.NA, pd.NA],
            "entry_bearish_class": [pd.NA, pd.NA, pd.NA],
            "close_bullish_class": [pd.NA, pd.NA, "strong"],
            "close_bearish_class": [pd.NA, pd.NA, pd.NA],
        },
        index=index,
    )
    entry_column = "entry_bullish_class" if direction == EntryDirection.BULLISH else "entry_bearish_class"
    frame.loc[index[0], entry_column] = "strong"
    return frame


def _premium_frame(option_type: str) -> pd.DataFrame:
    index = pd.date_range("2026-04-13 09:15", periods=3, freq="15min")
    base = 100.0 if option_type == "CE" else 120.0
    return pd.DataFrame(
        {
            "open": [base, base + 2.0, base + 4.0],
            "high": [base + 1.0, base + 3.0, base + 5.0],
            "low": [base - 1.0, base + 1.0, base + 3.0],
            "close": [base + 0.5, base + 2.5, base + 4.5],
        },
        index=index,
    )


def test_overnight_option_backtest_turns_bullish_signal_into_ce_trade(monkeypatch) -> None:
    config = AppConfig(
        strategy=StrategyConfig(stop_loss_percent=None, take_profit_percent=None),
        data=DataConfig(from_date="2026-04-13", to_date="2026-04-16"),
    )
    engine = OvernightOptionBacktestEngine(config, _FakeClient())
    prepared = _prepared_frame(EntryDirection.BULLISH)
    monkeypatch.setattr(engine, "prepare", lambda candles: prepared)
    monkeypatch.setattr(
        "ichimoku_framework.backtest.options.load_expired_upstox_ohlc",
        lambda client, expired_instrument_key, timeframe, from_date, to_date: _premium_frame("CE"),
    )

    result = engine.run(prepared)

    assert len(result.trades) == 1
    trade = result.trades[0]
    assert trade.option_type == "CE"
    assert trade.instrument_key == "ce-24000"
    assert trade.reason == ExitReason.CLOSE_SIGNAL
    assert trade.quantity == 75


def test_overnight_option_backtest_turns_bearish_signal_into_pe_trade(monkeypatch) -> None:
    config = AppConfig(
        strategy=StrategyConfig(stop_loss_percent=None, take_profit_percent=None),
        data=DataConfig(from_date="2026-04-13", to_date="2026-04-16"),
    )
    engine = OvernightOptionBacktestEngine(config, _FakeClient())
    prepared = _prepared_frame(EntryDirection.BEARISH)
    monkeypatch.setattr(engine, "prepare", lambda candles: prepared)
    monkeypatch.setattr(
        "ichimoku_framework.backtest.options.load_expired_upstox_ohlc",
        lambda client, expired_instrument_key, timeframe, from_date, to_date: _premium_frame("PE"),
    )

    result = engine.run(prepared)

    assert len(result.trades) == 1
    trade = result.trades[0]
    assert trade.option_type == "PE"
    assert trade.instrument_key == "pe-24000"
    assert trade.reason == ExitReason.CLOSE_SIGNAL
    assert trade.quantity == 75
