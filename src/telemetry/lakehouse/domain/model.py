"""Lakehouse storage domain core.

Pure Python: imports no framework, cloud SDK, or object store.
Business rules for writing projected telemetry events to a durable,
queryable lakehouse — partitioned, idempotent, stateless.
Adapters implement the ports defined in :mod:`ports`.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Protocol, runtime_checkable


class InvalidSchemaError(ValueError):
    """Raised when a projected event fails schema validation."""


class DuplicateOffsetError(ValueError):
    """Raised when an event would reuse an already-consumed offset."""


@dataclass(frozen=True)
class LakehouseRow:
    """An immutable row written to the lakehouse.

    Attributes:
        device_id: stable identifier of the device.
        sequence: monotonically increasing per-device sequence number.
        offset: Kafka offset of the source event (idempotency key).
        event_date: date of the event (partition key, UTC).
        payload: projected telemetry payload.
        written_at: when the row was written (UTC).
    """

    device_id: str
    sequence: int
    offset: int
    event_date: str
    payload: dict
    written_at: datetime

    def partition_path(self) -> str:
        """Object storage partition path: device_id={id}/event_date={date}/."""
        return f"device_id={self.device_id}/event_date={self.event_date}/"

    def row_key(self) -> str:
        """Unique row key: offset hash for idempotency."""
        return hashlib.sha256(
            f"{self.device_id}|{self.offset}".encode("utf-8")
        ).hexdigest()[:16]


@dataclass(frozen=True)
class WriteTelemetryCommand:
    """Input to the write use case."""

    device_id: str
    sequence: int
    offset: int
    event_date: str
    payload: dict


@dataclass(frozen=True)
class WriteTelemetryResult:
    """Outcome of writing a lakehouse row."""

    written: bool
    device_id: str
    sequence: int
    offset: int
    partition_path: str
    row_key: str


@runtime_checkable
class LakehouseStorage(Protocol):
    """Port: durable, queryable object store (e.g. S3 + Parquet).

    The domain depends on this interface only. Adapters implement it.
    """

    def write(self, partition_path: str, row_key: str, row: LakehouseRow) -> None:
        """Write ``row`` to ``partition_path`` under ``row_key``.

        Raises DuplicateOffsetError if ``row_key`` already exists (idempotency).
        """

    def exists(self, partition_path: str, row_key: str) -> bool:
        """Return True if a row with ``row_key`` already exists at ``partition_path``."""


@runtime_checkable
class LakehouseCatalog(Protocol):
    """Port: table registration / catalog (e.g. Glue crawler)."""

    def register_table(self, table_name: str, partition_path: str) -> None:
        """Register a table for analytics queries."""

    def table_exists(self, table_name: str) -> bool:
        """Return True if ``table_name`` is registered."""


@runtime_checkable
class Clock(Protocol):
    """Port: injectable time seam for deterministic tests."""

    def now(self) -> datetime:
        """Return the current UTC time."""


@dataclass(frozen=True)
class WriteTelemetry:
    """Domain service: write, partition, idempotency, catalog registration.

    Stateless: holds no device state. Idempotency is keyed by device_id +
    offset. The domain core imports no cloud SDK — adapters implement S3,
    Parquet, Glue.
    """

    def __init__(
        self,
        storage: LakehouseStorage,
        catalog: LakehouseCatalog,
        clock: Clock,
    ) -> None:
        object.__setattr__(self, "_storage", storage)
        object.__setattr__(self, "_catalog", catalog)
        object.__setattr__(self, "_clock", clock)

    def write(self, command: WriteTelemetryCommand) -> WriteTelemetryResult:
        """Write one projected telemetry event to the lakehouse.

        1. Validate schema (rejected events are never written).
        2. Build the immutable LakehouseRow aggregate.
        3. Check idempotency (skip if offset already written).
        4. Write to partitioned object storage.
        5. Register the table in the catalog.
        """
        self._validate_schema(command.payload)

        event_date = command.event_date or self._clock.now().strftime("%Y-%m-%d")
        row = LakehouseRow(
            device_id=command.device_id,
            sequence=command.sequence,
            offset=command.offset,
            event_date=event_date,
            payload=command.payload,
            written_at=self._clock.now(),
        )

        partition_path = row.partition_path()
        row_key = row.row_key()

        if self._storage.exists(partition_path, row_key):
            # Idempotent skip — same offset already written.
            return WriteTelemetryResult(
                written=False,
                device_id=command.device_id,
                sequence=command.sequence,
                offset=command.offset,
                partition_path=partition_path,
                row_key=row_key,
            )

        self._storage.write(partition_path, row_key, row)
        self._catalog.register_table(
            f"telemetry_{command.device_id.replace('-', '_')}", partition_path
        )

        return WriteTelemetryResult(
            written=True,
            device_id=command.device_id,
            sequence=command.sequence,
            offset=command.offset,
            partition_path=partition_path,
            row_key=row_key,
        )

    def _validate_schema(self, payload: dict) -> None:
        if not isinstance(payload, dict):
            raise InvalidSchemaError("payload must be a JSON object")
        if not payload:
            raise InvalidSchemaError("payload must not be empty")
