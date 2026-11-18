"""Telemetry ingestion domain core.

Pure Python: imports no framework, ORM, HTTP library, or message bus.
Business rules live here. Adapters implement the ports defined in :mod:`ports`.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol, runtime_checkable

from telemetry.domain.exceptions import DuplicateOffsetError, InvalidSchemaError


@dataclass(frozen=True)
class TelemetryEvent:
    """An immutable telemetry fact — an append-only event, never mutated.

    Attributes:
        device_id: stable identifier of the emitting device.
        sequence: monotonically increasing per-device sequence number.
        payload: device-generated telemetry payload (opaque to ingestion).
        timestamp: when the device emitted the event (UTC).
    """

    device_id: str
    sequence: int
    payload: dict
    timestamp: datetime

    def __post_init__(self) -> None:
        if not self.device_id or not self.device_id.strip():
            raise InvalidSchemaError("device_id is required")
        if self.sequence < 1:
            raise InvalidSchemaError("sequence must be >= 1")
        if not isinstance(self.payload, dict):
            raise InvalidSchemaError("payload must be a JSON object")
        if self.timestamp.tzinfo is None:
            object.__setattr__(self, "timestamp", self.timestamp.replace(tzinfo=timezone.utc))

    @property
    def event_id(self) -> str:
        """Stable content address: device|sequence|timestamp."""
        return f"{self.device_id}|{self.sequence}|{self.timestamp.isoformat()}"


@dataclass(frozen=True)
class IngestResult:
    """Outcome of accepting a telemetry event."""

    accepted: bool
    event_id: str
    offset: int
    device_id: str
    sequence: int


@runtime_checkable
class TelemetryBus(Protocol):
    """Port: durable, ordered, replayable event bus (e.g. Kafka).

    The domain depends on this interface only. Adapters implement it.
    """

    def append(self, device_id: str, event: TelemetryEvent) -> int:
        """Append ``event`` for ``device_id``; return the assigned offset.

        Raises DuplicateOffsetError if the offset is already consumed.
        """

    def read(self, device_id: str, from_offset: int) -> list[TelemetryEvent]:
        """Read events for ``device_id`` starting at ``from_offset``."""


@runtime_checkable
class TelemetrySchema(Protocol):
    """Port: schema validation enforced at the adapter boundary."""

    def validate(self, payload: dict) -> None:
        """Validate ``payload``; raise InvalidSchemaError if invalid."""


@runtime_checkable
class Clock(Protocol):
    """Port: injectable time seam for deterministic tests."""

    def now(self) -> datetime:
        """Return the current UTC time."""


@dataclass(frozen=True)
class IngestTelemetryCommand:
    """Input to the ingest use case (a command, not a domain event)."""

    device_id: str
    sequence: int
    payload: dict
    timestamp: datetime | None = None


class TelemetryIngestion:
    """Domain service: accept, validate, order, append telemetry events.

    Stateless: holds no device state. Per-device ordering is delegated to the
    bus (partition key = device_id). The current device state is a projection
    owned by the consumer, not stored here — event sourcing.
    """

    def __init__(self, bus: TelemetryBus, schema: TelemetrySchema, clock: Clock) -> None:
        self._bus = bus
        self._schema = schema
        self._clock = clock

    def ingest(self, command: IngestTelemetryCommand) -> IngestResult:
        """Accept one telemetry event.

        1. Validate schema (rejected events are never persisted).
        2. Build the immutable TelemetryEvent aggregate.
        3. Append to the bus (per-device partition -> ordered, replayable).
        """
        self._schema.validate(command.payload)

        stamp = command.timestamp or self._clock.now()
        event = TelemetryEvent(
            device_id=command.device_id,
            sequence=command.sequence,
            payload=command.payload,
            timestamp=stamp,
        )

        offset = self._bus.append(command.device_id, event)

        return IngestResult(
            accepted=True,
            event_id=event.event_id,
            offset=offset,
            device_id=command.device_id,
            sequence=command.sequence,
        )
