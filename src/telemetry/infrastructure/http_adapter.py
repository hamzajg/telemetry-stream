"""FastAPI HTTP adapter implementing the ingestion API entry point.

Thin adapter: parses HTTP, delegates to the application use case, returns
HTTP responses. Contains no business rules.
"""

from __future__ import annotations

from typing import Any, Dict

try:  # FastAPI is optional; the domain core does not depend on it
    from fastapi import FastAPI, HTTPException
    from fastapi.middleware.cors import CORSMiddleware
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

    class CORSMiddleware:  # type: ignore
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            pass


from datetime import datetime, timezone

from telemetry.application.ingest import (
    IngestTelemetry,
    IngestTelemetryRequest,
)
from telemetry.device.application.use_cases import (
    DeviceApplication,
    RegisterDeviceRequest as DeviceRegisterRequest,
)
from telemetry.domain.exceptions import InvalidSchemaError
from telemetry.domain.ports import TelemetryBus


class IngestEvent(BaseModel):
    device_id: str
    sequence: int
    payload: dict
    timestamp: str | None = None


class RegisterDeviceRequest(BaseModel):
    device_id: str


class DeviceOut(BaseModel):
    device_id: str
    registered_at: str
    active: bool


class SeedEvent(BaseModel):
    device_id: str
    sequence: int
    payload: dict
    timestamp: str | None = None


class TelemetryMetrics:
    """Simple observability counters for the ingestion adapter.

    Tracks accept/reject counts and per-device consumer lag.
    """

    def __init__(self) -> None:
        self.accept_count = 0
        self.reject_count = 0
        self._consumed_offset: dict[str, int] = {}

    def record_accept(self) -> None:
        self.accept_count += 1

    def record_reject(self) -> None:
        self.reject_count += 1

    def mark_consumed(self, device_id: str, offset: int) -> None:
        self._consumed_offset[device_id] = max(
            self._consumed_offset.get(device_id, 0), offset
        )

    def consumer_lag(self, device_id: str, latest_offset: int) -> int:
        consumed = self._consumed_offset.get(device_id, 0)
        return max(0, latest_offset - consumed)

    def snapshot(self) -> dict[str, Any]:
        return {
            "accept_count": self.accept_count,
            "reject_count": self.reject_count,
        }


def create_app(
    ingest_telemetry: IngestTelemetry,
    bus: TelemetryBus | None = None,
    device_app: DeviceApplication | None = None,
    metrics: TelemetryMetrics | None = None,
) -> Any:
    """Build the FastAPI app wired to the ingest use case.

    ``bus`` is optional; when provided, GET /v1/telemetry can read back
    stored events for dashboard display.

    ``device_app`` is optional; when provided, device management endpoints
    (GET /v1/devices, POST /v1/devices/register) are exposed.

    ``metrics`` is optional; when provided, GET /v1/metrics exposes
    accept/reject counters and consumer lag.
    """
    if FastAPI is None:  # pragma: no cover
        raise RuntimeError("FastAPI is not installed")

    app = FastAPI(title="Telemetry Ingestion")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    if metrics is None:
        metrics = TelemetryMetrics()

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
            metrics.record_reject()
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        metrics.record_accept()
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
            if device_id is not None:
                events = bus.read(device_id, 1)
            else:
                events = []
                for did in bus.device_ids():
                    events.extend(bus.read(did, 1))
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

    if device_app is not None:

        @app.get("/v1/devices")
        async def list_devices() -> Dict[str, Any]:
            result = device_app.query_devices()
            return {
                "active_count": result.active_count,
                "devices": [
                    {
                        "device_id": d.device_id,
                        "registered_at": d.registered_at.isoformat(),
                        "active": d.active,
                    }
                    for d in result.devices
                ],
            }

        @app.post("/v1/devices/register")
        async def register_device(req: RegisterDeviceRequest) -> Dict[str, Any]:
            try:
                result = device_app.register_device(
                    DeviceRegisterRequest(device_id=req.device_id)
                )
            except Exception as exc:  # pragma: no cover - adapter boundary
                raise HTTPException(status_code=400, detail=str(exc)) from exc
            return {
                "registered": result.registered,
                "device_id": result.device_id,
                "active": result.active,
            }

    if metrics is not None:

        @app.get("/v1/metrics")
        async def get_metrics() -> Dict[str, Any]:
            lag_by_device: dict[str, int] = {}
            if bus is not None:
                # Read all devices' events to compute latest offset per device
                # For simplicity, compute lag for devices that have been consumed
                for device_id in metrics._consumed_offset:
                    events = bus.read(device_id, 1)
                    latest = len(events)
                    lag_by_device[device_id] = metrics.consumer_lag(
                        device_id, latest
                    )
            return {
                **metrics.snapshot(),
                "consumer_lag_by_device": lag_by_device,
            }

    if ingest_telemetry is not None and bus is not None:

        @app.post("/v1/seed")
        async def seed(events: list[SeedEvent]) -> Dict[str, Any]:
            """Seed demo telemetry events into the bus.

            Useful for populating the dashboard without calling each
            /v1/telemetry endpoint individually.
            """
            accepted = 0
            rejected = 0
            for ev in events:
                try:
                    result = ingest_telemetry.execute(
                        IngestTelemetryRequest(
                            device_id=ev.device_id,
                            sequence=ev.sequence,
                            payload=ev.payload,
                            timestamp=ev.timestamp,
                        )
                    )
                    if result.accepted:
                        accepted += 1
                    else:
                        rejected += 1
                except InvalidSchemaError:
                    rejected += 1
            return {
                "accepted": accepted,
                "rejected": rejected,
                "total": accepted + rejected,
            }

    return app
