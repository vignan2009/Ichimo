from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any
from urllib.parse import quote

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

    def historical_candles_v3(
        self,
        instrument_key: str,
        unit: str,
        interval: str,
        to_date: str,
        from_date: str | None = None,
    ) -> dict[str, Any]:
        suffix = f"/{from_date}" if from_date else ""
        encoded_key = quote(instrument_key, safe="")
        url = f"{self.config.base_url}/v3/historical-candle/{encoded_key}/{unit}/{interval}/{to_date}{suffix}"
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

    def option_contracts(self, instrument_key: str, expiry_date: str | None = None) -> dict[str, Any]:
        url = f"{self.config.base_url}/v2/option/contract"
        params = {"instrument_key": instrument_key}
        if expiry_date is not None:
            params["expiry_date"] = expiry_date
        response = requests.get(url, headers=self.headers, params=params, timeout=self.config.timeout_seconds)
        response.raise_for_status()
        return response.json()

    def expired_expiries(self, instrument_key: str) -> dict[str, Any]:
        url = f"{self.config.base_url}/v2/expired-instruments/expiries"
        response = requests.get(url, headers=self.headers, params={"instrument_key": instrument_key}, timeout=self.config.timeout_seconds)
        response.raise_for_status()
        return response.json()

    def expired_option_contracts(self, instrument_key: str, expiry_date: str) -> dict[str, Any]:
        url = f"{self.config.base_url}/v2/expired-instruments/option/contract"
        response = requests.get(
            url,
            headers=self.headers,
            params={"instrument_key": instrument_key, "expiry_date": expiry_date},
            timeout=self.config.timeout_seconds,
        )
        response.raise_for_status()
        return response.json()

    def expired_historical_candles(
        self,
        expired_instrument_key: str,
        interval: str,
        to_date: str,
        from_date: str,
    ) -> dict[str, Any]:
        encoded_key = quote(expired_instrument_key, safe="")
        url = f"{self.config.base_url}/v2/expired-instruments/historical-candle/{encoded_key}/{interval}/{to_date}/{from_date}"
        logger.info("Fetching expired historical candles for {}", expired_instrument_key)
        response = requests.get(url, headers=self.headers, timeout=self.config.timeout_seconds)
        response.raise_for_status()
        return response.json()
