"""Stream processing domain core.

Pure Python: imports no framework, ORM, HTTP library, or message bus.
Business rules for projecting telemetry events into current device state.
Adapters implement the ports defined in :mod:`ports`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Protocol, runtime_checkable


class InvalidSchemaError(ValueError):
    """Raised when a telemetry event fails schema validation."""


class OutOfOrderEventError(ValueError):
    """Raised when an event arrives with a sequence <= the projected sequence."""


@dataclass(frozen=True)
class DeviceState:
    """Current projected state for a single device — the event sourcing read model.

    Attributes:
        device_id: stable identifier of the device.
        latest_sequence: highest sequence number projected so far.
        latest_reading: the most recent telemetry payload.
        last_updated_at: when the projection was last updated (UTC).
    """

    device_id: str
    latest_sequence: int
    latest_reading: dict
    last_updated_at: datetime

    @classmethod
    def initial(cls, device_id: str) -> "DeviceState":
        return cls(
            device_id=device_id,
            latest_sequence=0,
            latest_reading={},
            last_updated_at=datetime.min.replace(tzinfo=timezone.utc),
        )

    def is_newer(self, sequence: int) -> bool:
        """True if ``sequence`` advances the projection."""
        return sequence > self.latest_sequence

    def advance(self, sequence: int, reading: dict, updated_at: datetime) -> "DeviceState":
        """Return a new DeviceState advanced to ``sequence`` (immutable)."""
        return DeviceState(
            device_id=self.device_id,
            latest_sequence=sequence,
            latest_reading=reading,
            last_updated_at=updated_at,
        )


@dataclass(frozen=True)
class ProjectTelemetryCommand:
    """Input to the project use case."""

    device_id: str
    sequence: int
    payload: dict
    offset: int
    timestamp: datetime | None = None


@dataclass(frozen=True)
class ProjectTelemetryResult:
    """Outcome of projecting a telemetry event."""

    projected: bool
    device_id: str
    sequence: int
    offset: int


@runtime_checkable
class TelemetryProjection(Protocol):
    """Port: current-device-state projection store (e.g. in-memory dict, DB)."""

    def get(self, device_id: str) -> DeviceState | None:
        """Return the current projection for ``device_id``, or None if absent."""

    def save(self, device_id: str, state: DeviceState) -> None:
        """Persist the projection for ``device_id``."""


@runtime_checkable
class TelemetrySchema(Protocol):
    """Port: schema validation enforced at the consumer boundary."""

    def validate(self, payload: dict) -> None:
        """Validate ``payload``; raise InvalidSchemaError if invalid."""


@runtime_checkable
class Clock(Protocol):
    """Port: injectable time seam for deterministic tests."""

    def now(self) -> datetime:
        """Return the current UTC time."""


class ProjectTelemetry:
    """Domain service: read, validate, order, project telemetry events.

    Stateless: holds no device state. The projection is the read model,
    derived from the event stream (Kafka is the source of truth).
    """

    def __init__(
        self,
        projection: TelemetryProjection,
        schema: TelemetrySchema,
        clock: Clock,
    ) -> None:
        self._projection = projection
        self._schema = schema
        self._clock = clock

    def project(self, command: ProjectTelemetryCommand) -> ProjectTelemetryResult:
        """Project one telemetry event into current device state.

        1. Validate schema (rejected events are never projected).
        2. Load current projection (or initial state).
        3. Guard ordering: only advance if sequence > latest_sequence.
        4. Save the new projection.
        """
        self._schema.validate(command.payload)

        current = self._projection.get(command.device_id) or DeviceState.initial(
            command.device_id
        )

        if not current.is_newer(command.sequence):
            # Duplicate or out-of-order event — idempotent skip.
            return ProjectTelemetryResult(
                projected=False,
                device_id=command.device_id,
                sequence=command.sequence,
                offset=command.offset,
            )

        stamp = command.timestamp or self._clock.now()
        state = current.advance(command.sequence, command.payload, stamp)
        self._projection.save(command.device_id, state)

        return ProjectTelemetryResult(
            projected=True,
            device_id=command.device_id,
            sequence=command.sequence,
            offset=command.offset,
        )
