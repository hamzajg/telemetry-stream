"""System clock adapter implementing the Clock port."""

from __future__ import annotations

from datetime import datetime, timezone

from telemetry.domain.ports import Clock


class SystemClock(Clock):
    """Real-time clock."""

    def now(self) -> datetime:
        return datetime.now(timezone.utc)
