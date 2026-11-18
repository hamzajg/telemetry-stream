"""Ingest telemetry use case.

Application layer: orchestrates the domain service and adapters. Depends on
ports (interfaces), not on concrete Kafka/HTTP/schema implementations.
"""

from __future__ import annotations

from dataclasses import dataclass

from telemetry.domain.exceptions import IngestionError
from telemetry.domain.model import (
    IngestResult,
    IngestTelemetryCommand,
    TelemetryIngestion,
)
from telemetry.domain.ports import Clock, TelemetryBus, TelemetrySchema


@dataclass(frozen=True)
class IngestTelemetryRequest:
    device_id: str
    sequence: int
    payload: dict
    timestamp: str | None = None


@dataclass(frozen=True)
class IngestTelemetryResponse:
    accepted: bool
    event_id: str
    offset: int
    device_id: str
    sequence: int


class IngestTelemetry:
    """Use case: ingest one telemetry event through the domain service."""

    def __init__(self, ingestion: TelemetryIngestion, clock: Clock) -> None:
        self._ingestion = ingestion
        self._clock = clock

    def execute(self, request: IngestTelemetryRequest) -> IngestTelemetryResponse:
        from datetime import datetime

        stamp = None
        if request.timestamp is not None:
            stamp = datetime.fromisoformat(request.timestamp)

        result = self._ingestion.ingest(
            IngestTelemetryCommand(
                device_id=request.device_id,
                sequence=request.sequence,
                payload=request.payload,
                timestamp=stamp,
            )
        )
        return IngestTelemetryResponse(
            accepted=result.accepted,
            event_id=result.event_id,
            offset=result.offset,
            device_id=result.device_id,
            sequence=result.sequence,
        )
