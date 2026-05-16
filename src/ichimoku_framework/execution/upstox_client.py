from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

import requests
from dotenv import load_dotenv
from loguru import logger

from ichimoku_framework.config.models import UpstoxConfig


load_dotenv()


@dataclass(slots=True)
class UpstoxClient:
    """Thin REST adapter kept intentionally small for easy mocking."""

    config: UpstoxConfig

    @property
    def access_token(self) -> str:
        token = os.getenv(self.config.access_token_env)
        if not token:
            raise RuntimeError(f"Missing access token env var: {self.config.access_token_env}")
        return token

    @property
    def headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.access_token}", "Accept": "application/json"}

    def historical_candles(self, instrument_key: str, interval: str, to_date: str, from_date: str | None = None) -> dict[str, Any]:
        suffix = f"/{from_date}" if from_date else ""
        url = f"{self.config.base_url}/v2/historical-candle/{instrument_key}/{interval}/{to_date}{suffix}"
        logger.info("Fetching historical candles for {}", instrument_key)
        response = requests.get(url, headers=self.headers, timeout=self.config.timeout_seconds)
        response.raise_for_status()
        return response.json()

    def place_order(self, payload: dict[str, Any]) -> dict[str, Any]:
        url = f"{self.config.hft_base_url}/v3/order/place"
        response = requests.post(url, headers={**self.headers, "Content-Type": "application/json"}, json=payload, timeout=self.config.timeout_seconds)
        response.raise_for_status()
        return response.json()

    def option_chain(self, instrument_key: str, expiry_date: str) -> dict[str, Any]:
        url = f"{self.config.base_url}/v2/option/chain"
        response = requests.get(url, headers=self.headers, params={"instrument_key": instrument_key, "expiry_date": expiry_date}, timeout=self.config.timeout_seconds)
        response.raise_for_status()
        return response.json()
