from __future__ import annotations

from datetime import datetime, time
from enum import Enum
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field


class ConditionMode(str, Enum):
    ANY = "ANY"
    ALL = "ALL"


class SignalClass(str, Enum):
    STRONG = "strong"
    NEUTRAL = "neutral"
    WEAK = "weak"


class StrategyConfig(BaseModel):
    start_datetime: datetime = datetime(2023, 1, 1)
    end_datetime: datetime = datetime(2030, 1, 1)
    entry_tenkan_period: int = 9
    entry_kijun_period: int = 26
    entry_senkou_b_period: int = 52
    entry_displacement: int = 26
    close_tenkan_period: int = 9
    close_kijun_period: int = 26
    close_senkou_b_period: int = 52
    close_displacement: int = 26
    enabled_entry_bullish_classes: list[SignalClass] = Field(default_factory=lambda: [SignalClass.STRONG])
    enabled_entry_bearish_classes: list[SignalClass] = Field(default_factory=lambda: [SignalClass.STRONG])
    enabled_close_bullish_classes: list[SignalClass] = Field(default_factory=lambda: [SignalClass.STRONG])
    enabled_close_bearish_classes: list[SignalClass] = Field(default_factory=lambda: [SignalClass.STRONG])
    entry_condition_mode: ConditionMode = ConditionMode.ANY
    close_condition_mode: ConditionMode = ConditionMode.ANY
    stop_loss_percent: float | None = -2.0
    take_profit_percent: float | None = 5.0
    atr_period: int = 14
    atr_stop_multiplier: float | None = None
    atr_take_profit_multiplier: float | None = None
    max_daily_loss: float | None = None
    max_concurrent_trades: int = 1
    session_start: time = time(0, 0)
    session_end: time = time(23, 59, 59)
    timezone: str = "Asia/Kolkata"


class BacktestConfig(BaseModel):
    initial_capital: float = 100000.0
    quantity: int = 1
    commission_per_order: float = 0.0
    slippage_bps: float = 0.0
    intrabar_policy: Literal["worst_case"] = "worst_case"


class OptionsConfig(BaseModel):
    enabled: bool = False
    underlying: Literal["NIFTY", "BANKNIFTY", "FINNIFTY"] = "NIFTY"
    strike_step: int = 50
    expiry_policy: Literal["nearest"] = "nearest"
    slippage_bps: float = 0.0


class UpstoxConfig(BaseModel):
    access_token_env: str = "UPSTOX_ACCESS_TOKEN"
    base_url: str = "https://api.upstox.com"
    hft_base_url: str = "https://api-hft.upstox.com"
    timeout_seconds: int = 10


class AppConfig(BaseModel):
    strategy: StrategyConfig = Field(default_factory=StrategyConfig)
    backtest: BacktestConfig = Field(default_factory=BacktestConfig)
    options: OptionsConfig = Field(default_factory=OptionsConfig)
    upstox: UpstoxConfig = Field(default_factory=UpstoxConfig)

    @classmethod
    def from_yaml(cls, path: str | Path) -> "AppConfig":
        with Path(path).open("r", encoding="utf-8") as handle:
            return cls.model_validate(yaml.safe_load(handle))
