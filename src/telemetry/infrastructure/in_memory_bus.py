"""In-memory test double for the TelemetryBus port.

Pure Python, no Kafka. Used by domain/core tests so they run without a
message bus. Not used in production.
"""

from __future__ import annotations

from typing import Dict, List

from telemetry.domain.model import TelemetryEvent
from telemetry.domain.ports import TelemetryBus


class InMemoryTelemetryBus(TelemetryBus):
    """Append-only in-memory bus keyed by device_id with per-device offsets."""

    def __init__(self) -> None:
        self._events: Dict[str, List[TelemetryEvent]] = {}
        self._offsets: Dict[str, int] = {}

    def append(self, device_id: str, event: TelemetryEvent) -> int:
        events = self._events.setdefault(device_id, [])
        offset = len(events) + 1
        events.append(event)
        self._offsets[device_id] = offset
        return offset

    def read(self, device_id: str, from_offset: int) -> List[TelemetryEvent]:
        events = self._events.get(device_id, [])
        return [e for i, e in enumerate(events, start=1) if i >= from_offset]

    def device_ids(self) -> list[str]:
        """Return all device IDs that have events."""
        return sorted(self._events.keys())
