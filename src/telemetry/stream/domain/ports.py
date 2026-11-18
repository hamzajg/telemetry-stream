"""Ports: interfaces the stream domain depends on. Adapters implement these."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol, runtime_checkable

from telemetry.stream.domain.model import DeviceState


@runtime_checkable
class TelemetryProjection(Protocol):
    """Current-device-state projection store (e.g. in-memory dict, DB)."""

    def get(self, device_id: str) -> DeviceState | None:
        """Return the current projection for ``device_id``, or None if absent."""

    def save(self, device_id: str, state: DeviceState) -> None:
        """Persist the projection for ``device_id``."""


@runtime_checkable
class TelemetrySchema(Protocol):
    """Schema validation enforced at the consumer boundary."""

    def validate(self, payload: dict) -> None:
        """Validate ``payload``; raise InvalidSchemaError if invalid."""


@runtime_checkable
class Clock(Protocol):
    """Injectable time seam for deterministic tests."""

    def now(self) -> datetime:
        """Return the current UTC time."""
