"""FastAPI HTTP adapter implementing the ingestion API entry point.

Thin adapter: parses HTTP, delegates to the application use case, returns
HTTP responses. Contains no business rules.

Adds production hardening:
- WebSocket /v1/ws/telemetry broadcasting newly ingested events to live clients
- API key authentication (X-API-Key header, TELEMETRY_API_KEY env var; dev mode
  when unset)
- Fixed-window rate limiting per client IP (TELEMETRY_RATE_LIMIT env var,
  requests per minute; dev mode unlimited when unset)
"""

from __future__ import annotations

import os
import time
from collections import defaultdict
from typing import Any, Dict, Set

try:  # FastAPI is optional; the domain core does not depend on it
    from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.security import APIKeyHeader
    from pydantic import BaseModel
    from starlette.status import HTTP_401_UNAUTHORIZED, HTTP_429_TOO_MANY_REQUESTS
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

    class WebSocket:  # type: ignore
        async def accept(self) -> None:
            pass

        async def send_text(self, data: str) -> None:
            pass

        async def close(self) -> None:
            pass

    class WebSocketDisconnect(Exception):  # type: ignore
        pass

    class CORSMiddleware:  # type: ignore
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            pass

    class APIKeyHeader:  # type: ignore
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            pass

    HTTP_401_UNAUTHORIZED = 401  # type: ignore
    HTTP_429_TOO_MANY_REQUESTS = 429  # type: ignore


from datetime import datetime, timezone

from telemetry.application.ingest import (
    IngestTelemetry,
    IngestTelemetryRequest,
)
from telemetry.device.application.use_cases import (
    CredentialApplication,
    DeviceApplication,
    ProvisionCredentialRequest as CredentialProvisionRequest,
    RegisterDeviceRequest as DeviceRegisterRequest,
    RevokeCredentialRequest as CredentialRevokeRequest,
    RotateCredentialRequest as CredentialRotateRequest,
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


class ProvisionCredential(BaseModel):
    device_id: str
    credential_id: str


class ProvisionCredentialOut(BaseModel):
    provisioned: bool
    device_id: str
    credential_id: str


class RevokeCredential(BaseModel):
    credential_id: str


class RevokeCredentialOut(BaseModel):
    revoked: bool
    credential_id: str


class RotateCredential(BaseModel):
    device_id: str
    old_credential_id: str
    new_credential_id: str


class RotateCredentialOut(BaseModel):
    rotated: bool
    device_id: str
    old_credential_id: str
    new_credential_id: str


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


class ConnectionManager:
    """Manages WebSocket connections for live telemetry broadcast."""

    def __init__(self) -> None:
        self.active: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active.add(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        self.active.discard(websocket)

    async def broadcast(self, message: Dict[str, Any]) -> None:
        import json

        text = json.dumps(message)
        dead: list[WebSocket] = []
        for ws in list(self.active):
            try:
                await ws.send_text(text)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)


class RateLimiter:
    """Fixed-window rate limiter keyed by client IP."""

    def __init__(self, limit: int | None) -> None:
        self.limit = limit
        self._windows: dict[str, tuple[float, int]] = {}

    def is_allowed(self, client_id: str) -> bool:
        if self.limit is None:
            return True
        now = time.time()
        window_start, count = self._windows.get(client_id, (now, 0))
        if now - window_start >= 60.0:
            window_start, count = now, 0
        count += 1
        self._windows[client_id] = (window_start, count)
        return count <= self.limit


def create_app(
    ingest_telemetry: IngestTelemetry,
    bus: TelemetryBus | None = None,
    device_app: DeviceApplication | None = None,
    credential_app: CredentialApplication | None = None,
    metrics: TelemetryMetrics | None = None,
) -> Any:
    """Build the FastAPI app wired to the ingest use case.

    ``bus`` is optional; when provided, GET /v1/telemetry can read back
    stored events for dashboard display and WebSocket broadcast works.

    ``device_app`` is optional; when provided, device management endpoints
    (GET /v1/devices, POST /v1/devices/register) are exposed.

    ``credential_app`` is optional; when provided, credential management
    endpoints (POST /v1/credentials/provision) are exposed.

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

    # Production hardening knobs (env-driven, dev-friendly defaults)
    api_key = os.environ.get("TELEMETRY_API_KEY")
    rate_limit_raw = os.environ.get("TELEMETRY_RATE_LIMIT")
    rate_limit = int(rate_limit_raw) if rate_limit_raw else None
    limiter = RateLimiter(rate_limit)
    manager = ConnectionManager()

    @app.middleware("http")
    async def auth_and_rate_limit(request, call_next):
        client_id = request.client.host if request.client else "unknown"
        if not limiter.is_allowed(client_id):
            from starlette.responses import JSONResponse

            return JSONResponse(
                status_code=HTTP_429_TOO_MANY_REQUESTS,
                content={"detail": "rate limit exceeded"},
            )
        expected = os.environ.get("TELEMETRY_API_KEY")
        if expected:
            provided = request.headers.get("x-api-key", "")
            if provided != expected:
                from starlette.responses import JSONResponse

                return JSONResponse(
                    status_code=HTTP_401_UNAUTHORIZED,
                    content={"detail": "invalid or missing API key"},
                )
        return await call_next(request)

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
        payload = {
            "accepted": result.accepted,
            "event_id": result.event_id,
            "offset": result.offset,
            "device_id": result.device_id,
            "sequence": result.sequence,
        }
        # Broadcast newly accepted event to live WebSocket clients
        if bus is not None and result.accepted:
            await manager.broadcast(
                {
                    "type": "telemetry",
                    "device_id": result.device_id,
                    "sequence": result.sequence,
                    "payload": event.payload,
                    "timestamp": event.timestamp,
                    "offset": result.offset,
                }
            )
        return payload

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

        @app.websocket("/v1/ws/telemetry")
        async def ws_telemetry(websocket: WebSocket) -> None:
            await manager.connect(websocket)
            try:
                while True:
                    # Keep the connection alive; ignore client messages
                    await websocket.receive_text()
            except WebSocketDisconnect:
                pass
            finally:
                manager.disconnect(websocket)

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

    if credential_app is not None:

        @app.post("/v1/credentials/provision")
        async def provision_credential(req: ProvisionCredential) -> ProvisionCredentialOut:
            try:
                result = credential_app.provision_credential(
                    CredentialProvisionRequest(
                        device_id=req.device_id,
                        credential_id=req.credential_id,
                    )
                )
            except Exception as exc:  # pragma: no cover - adapter boundary
                raise HTTPException(status_code=400, detail=str(exc)) from exc
            return ProvisionCredentialOut(
                provisioned=result.provisioned,
                device_id=result.device_id,
                credential_id=result.credential_id,
            )

        @app.post("/v1/credentials/revoke")
        async def revoke_credential(req: RevokeCredential) -> RevokeCredentialOut:
            try:
                result = credential_app.revoke_credential(
                    CredentialRevokeRequest(credential_id=req.credential_id)
                )
            except Exception as exc:  # pragma: no cover - adapter boundary
                raise HTTPException(status_code=400, detail=str(exc)) from exc
            return RevokeCredentialOut(
                revoked=result.revoked,
                credential_id=result.credential_id,
            )

        @app.post("/v1/credentials/rotate")
        async def rotate_credential(req: RotateCredential) -> RotateCredentialOut:
            try:
                result = credential_app.rotate_credential(
                    CredentialRotateRequest(
                        device_id=req.device_id,
                        old_credential_id=req.old_credential_id,
                        new_credential_id=req.new_credential_id,
                    )
                )
            except Exception as exc:  # pragma: no cover - adapter boundary
                raise HTTPException(status_code=400, detail=str(exc)) from exc
            return RotateCredentialOut(
                rotated=result.rotated,
                device_id=result.device_id,
                old_credential_id=result.old_credential_id,
                new_credential_id=result.new_credential_id,
            )

    if metrics is not None:

        @app.get("/v1/metrics")
        async def get_metrics() -> Dict[str, Any]:
            lag_by_device: dict[str, int] = {}
            if bus is not None:
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
