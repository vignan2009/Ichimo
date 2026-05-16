from __future__ import annotations

import pandas as pd

from ichimoku_framework.config.models import StrategyConfig
from ichimoku_framework.execution.options import contracts_from_payload, nearest_atm_contract
from ichimoku_framework.strategy.logic import EntryDirection, directional_entry


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
