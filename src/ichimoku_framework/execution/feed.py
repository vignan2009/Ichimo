from __future__ import annotations

from dataclasses import dataclass
from typing import Callable


@dataclass(slots=True)
class WebSocketFeed:
    """Lifecycle shell for a live feed implementation."""

    authorized_url_provider: Callable[[], str]
    on_message: Callable[[bytes], None]

    def connect(self) -> None:
        """Extension point for Upstox V3 protobuf websocket wiring."""
        raise NotImplementedError("Wire websocket-client here in the live deployment layer")

