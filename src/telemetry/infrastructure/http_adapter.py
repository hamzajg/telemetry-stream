"""FastAPI HTTP adapter implementing the ingestion API entry point.

Thin adapter: parses HTTP, delegates to the application use case, returns
HTTP responses. Contains no business rules.
"""

from __future__ import annotations

from typing import Any, Dict

try:  # FastAPI is optional; the domain core does not depend on it
    from fastapi import FastAPI, HTTPException
    from pydantic import BaseModel
except Exception:  # pragma: no cover - FastAPI may be absent in test envs
    FastAPI = None  # type: ignore

    class BaseModel:  # type: ignore
        def __init__(self, **kwargs: Any) -> None:
            for k, v in kwargs.items():
                setattr(self, k, v)

    class HTTPException(Exception):  # type: ignore
        def __init__(self, status_code: int, detail: str) -> None:
            self.status_code = status_code
            self.detail = detail


from telemetry.application.ingest import (
    IngestTelemetry,
    IngestTelemetryRequest,
)
from telemetry.domain.exceptions import InvalidSchemaError
from telemetry.domain.ports import TelemetryBus


class IngestEvent(BaseModel):
    device_id: str
    sequence: int
    payload: dict
    timestamp: str | None = None


def create_app(
    ingest_telemetry: IngestTelemetry,
    bus: TelemetryBus | None = None,
) -> Any:
    """Build the FastAPI app wired to the ingest use case.

    ``bus`` is optional; when provided, GET /v1/telemetry can read back
    stored events for dashboard display.
    """
    if FastAPI is None:  # pragma: no cover
        raise RuntimeError("FastAPI is not installed")

    app = FastAPI(title="Telemetry Ingestion")

    @app.post("/v1/telemetry")
    async def ingest(event: IngestEvent) -> Dict[str, Any]:
        try:
            result = ingest_telemetry.execute(
                IngestTelemetryRequest(
                    device_id=event.device_id,
                    sequence=event.sequence,
                    payload=event.payload,
                    timestamp=event.timestamp,
                )
            )
        except InvalidSchemaError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {
            "accepted": result.accepted,
            "event_id": result.event_id,
            "offset": result.offset,
            "device_id": result.device_id,
            "sequence": result.sequence,
        }

    if bus is not None:

        @app.get("/v1/telemetry")
        async def list_telemetry(
            device_id: str | None = None,
            limit: int = 100,
        ) -> Dict[str, Any]:
            events = bus.read(device_id, 1) if device_id is not None else []
            items = [
                {
                    "device_id": e.device_id,
                    "sequence": e.sequence,
                    "payload": e.payload,
                    "timestamp": e.timestamp.isoformat(),
                    "offset": i + 1,
                }
                for i, e in enumerate(events[:limit])
            ]
            return {"events": items, "count": len(items)}

    return app
