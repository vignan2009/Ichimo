from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Iterable


@dataclass(frozen=True, slots=True)
class OptionContract:
    instrument_key: str
    expiry: date
    strike_price: float
    option_type: str
    premium: float


def nearest_atm_contract(contracts: Iterable[OptionContract], spot_price: float, bullish: bool, expiry: date) -> OptionContract:
    option_type = "CE" if bullish else "PE"
    eligible = [contract for contract in contracts if contract.expiry == expiry and contract.option_type == option_type]
    if not eligible:
        raise ValueError("No eligible option contracts found")
    return min(eligible, key=lambda contract: abs(contract.strike_price - spot_price))


def premium_fill_price(premium: float, bullish: bool, slippage_bps: float) -> float:
    """Apply adverse slippage to option premium execution."""
    factor = slippage_bps / 10000.0
    return premium * (1 + factor if bullish else 1 + factor)
