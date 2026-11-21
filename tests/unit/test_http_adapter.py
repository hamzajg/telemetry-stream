"""HTTP adapter tests — FastAPI adapter with in-memory doubles."""

from __future__ import annotations

import unittest
from datetime import datetime, timezone

from fastapi.testclient import TestClient

from telemetry.application.ingest import IngestTelemetryRequest
from telemetry.device.application.use_cases import DeviceApplication
from telemetry.domain.model import (
    IngestResult,
    IngestTelemetryCommand,
    TelemetryEvent,
    TelemetryIngestion,
)
from telemetry.domain.ports import Clock, TelemetryBus
from telemetry.infrastructure.fixed_clock import FixedClock
from telemetry.infrastructure.http_adapter import create_app
from telemetry.infrastructure.in_memory_bus import InMemoryTelemetryBus


class _FixedNow(Clock):
    def __init__(self, instant: datetime) -> None:
        self._instant = instant

    def now(self) -> datetime:
        return self._instant


class _FakeIngest:
    def execute(self, request: IngestTelemetryCommand) -> IngestResult:
        return IngestResult(
            accepted=True,
            event_id=f"{request.device_id}|{request.sequence}|2026-01-01T00:00:00+00:00",
            offset=1,
            device_id=request.device_id,
            sequence=request.sequence,
        )


class _FakeDeviceApp(DeviceApplication):
    def __init__(self) -> None:
        self._devices = [
            type(
                "Device",
                (),
                {
                    "device_id": "device-42",
                    "registered_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
                    "active": True,
                },
            )(),
            type(
                "Device",
                (),
                {
                    "device_id": "device-99",
                    "registered_at": datetime(2026, 1, 2, tzinfo=timezone.utc),
                    "active": False,
                },
            )(),
        ]

    def query_devices(self):
        from telemetry.device.application.use_cases import QueryDevicesResponse

        return QueryDevicesResponse(
            active_count=1,
            devices=self._devices,
        )

    def register_device(self, request):
        from telemetry.device.application.use_cases import RegisterDeviceResponse

        return RegisterDeviceResponse(
            registered=True,
            device_id=request.device_id,
            active=True,
        )


class HttpAdapterTest(unittest.TestCase):
    def setUp(self) -> None:
        ingest = _FakeIngest()
        bus = InMemoryTelemetryBus()
        device_app = _FakeDeviceApp()
        self.app = create_app(ingest, bus=bus, device_app=device_app)
        self.client = TestClient(self.app)

    def test_get_telemetry_returns_events(self) -> None:
        bus = InMemoryTelemetryBus()
        event = TelemetryEvent(
            device_id="device-42",
            sequence=1,
            payload={"reading_type": "gps"},
            timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
        bus.append("device-42", event)

        app = create_app(_FakeIngest(), bus=bus)
        client = TestClient(app)

        res = client.get("/v1/telemetry?device_id=device-42")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["events"][0]["device_id"], "device-42")

    def test_get_devices_returns_registry(self) -> None:
        res = self.client.get("/v1/devices")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["active_count"], 1)
        self.assertEqual(len(data["devices"]), 2)
        ids = [d["device_id"] for d in data["devices"]]
        self.assertIn("device-42", ids)
        self.assertIn("device-99", ids)

    def test_post_register_device(self) -> None:
        res = self.client.post("/v1/devices/register", json={"device_id": "device-new"})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["registered"])
        self.assertEqual(data["device_id"], "device-new")


if __name__ == "__main__":
    unittest.main()
