"""Ports: interfaces the domain depends on. Adapters implement these."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol, runtime_checkable

from telemetry.domain.model import TelemetryEvent


@runtime_checkable
class TelemetryBus(Protocol):
    """Durable, ordered, replayable event bus (e.g. Kafka)."""

    def append(self, device_id: str, event: TelemetryEvent) -> int:
        """Append ``event`` for ``device_id``; return the assigned offset.

        Raises DuplicateOffsetError if the offset is already consumed.
        """

    def read(self, device_id: str, from_offset: int) -> list[TelemetryEvent]:
        """Read events for ``device_id`` starting at ``from_offset``."""


@runtime_checkable
class TelemetrySchema(Protocol):
    """Schema validation enforced at the adapter boundary."""

    def validate(self, payload: dict) -> None:
        """Validate ``payload``; raise InvalidSchemaError if invalid."""


@runtime_checkable
class Clock(Protocol):
    """Injectable time seam for deterministic tests."""

    def now(self) -> datetime:
        """Return the current UTC time."""
