from __future__ import annotations

from dataclasses import dataclass
from time import sleep
from typing import Any, Callable

from loguru import logger


@dataclass(slots=True)
class RetryPolicy:
    attempts: int = 3
    backoff_seconds: float = 0.5


class OrderManager:
    """Retry wrapper around a broker order function."""

    def __init__(self, submitter: Callable[[dict[str, Any]], dict[str, Any]], retry_policy: RetryPolicy | None = None) -> None:
        self.submitter = submitter
        self.retry_policy = retry_policy or RetryPolicy()

    def submit(self, payload: dict[str, Any]) -> dict[str, Any]:
        last_error: Exception | None = None
        for attempt in range(1, self.retry_policy.attempts + 1):
            try:
                return self.submitter(payload)
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                logger.warning("Order attempt {} failed: {}", attempt, exc)
                sleep(self.retry_policy.backoff_seconds * attempt)
        raise RuntimeError("Order submission failed after retries") from last_error

