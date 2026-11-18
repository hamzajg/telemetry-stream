"""Fixed clock test double implementing the Clock port."""

from __future__ import annotations

from datetime import datetime, timezone

from telemetry.domain.ports import Clock


class FixedClock(Clock):
    """Deterministic clock returning a fixed instant."""

    def __init__(self, instant: datetime) -> None:
        self._instant = instant

    def now(self) -> datetime:
        return self._instant
