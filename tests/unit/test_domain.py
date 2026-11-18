"""Domain core tests — pure Python, no Kafka, no HTTP, no framework.

These run against in-memory doubles implementing the ports, proving the
domain is independently testable (hexagonal: policy depends on nothing).
"""

from __future__ import annotations

import unittest
from datetime import datetime, timezone

from telemetry.domain.exceptions import DuplicateOffsetError, InvalidSchemaError
from telemetry.domain.model import (
    IngestResult,
    IngestTelemetryCommand,
    TelemetryEvent,
    TelemetryIngestion,
)
from telemetry.domain.ports import Clock, TelemetryBus, TelemetrySchema
from telemetry.infrastructure.fixed_clock import FixedClock
from telemetry.infrastructure.in_memory_bus import InMemoryTelemetryBus
from telemetry.infrastructure.json_schema_adapter import JsonSchemaAdapter


class _FixedNow(Clock):
    def __init__(self, instant: datetime) -> None:
        self._instant = instant

    def now(self) -> datetime:
        return self._instant


class TelemetryEventTest(unittest.TestCase):
    def test_valid_event(self) -> None:
        event = TelemetryEvent(
            device_id="device-42",
            sequence=1,
            payload={"reading_type": "gps", "value": 1.5},
            timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
        self.assertEqual(event.device_id, "device-42")
        self.assertEqual(event.sequence, 1)
        self.assertEqual(
            event.event_id,
            "device-42|1|2026-01-01T00:00:00+00:00",
        )

    def test_empty_device_id_rejected(self) -> None:
        with self.assertRaises(InvalidSchemaError):
            TelemetryEvent(
                device_id="",
                sequence=1,
                payload={"reading_type": "gps", "value": 1.5},
                timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc),
            )

    def test_zero_sequence_rejected(self) -> None:
        with self.assertRaises(InvalidSchemaError):
            TelemetryEvent(
                device_id="device-42",
                sequence=0,
                payload={"reading_type": "gps", "value": 1.5},
                timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc),
            )

    def test_non_dict_payload_rejected(self) -> None:
        with self.assertRaises(InvalidSchemaError):
            TelemetryEvent(
                device_id="device-42",
                sequence=1,
                payload="not-a-dict",  # type: ignore[arg-type]
                timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc),
            )

    def test_naive_timestamp_becomes_utc(self) -> None:
        event = TelemetryEvent(
            device_id="device-42",
            sequence=1,
            payload={"reading_type": "gps", "value": 1.5},
            timestamp=datetime(2026, 1, 1),
        )
        self.assertIsNotNone(event.timestamp.tzinfo)


class JsonSchemaAdapterTest(unittest.TestCase):
    def test_valid_payload_passes(self) -> None:
        adapter = JsonSchemaAdapter()
        adapter.validate({"reading_type": "gps", "value": 1.5})

    def test_missing_field_rejected(self) -> None:
        adapter = JsonSchemaAdapter()
        with self.assertRaises(InvalidSchemaError):
            adapter.validate({"reading_type": "gps"})

    def test_non_dict_rejected(self) -> None:
        adapter = JsonSchemaAdapter()
        with self.assertRaises(InvalidSchemaError):
            adapter.validate("not-a-dict")  # type: ignore[arg-type]

    def test_wrong_value_type_rejected(self) -> None:
        adapter = JsonSchemaAdapter()
        with self.assertRaises(InvalidSchemaError):
            adapter.validate({"reading_type": "gps", "value": "not-a-number"})


class InMemoryBusTest(unittest.TestCase):
    def test_append_returns_per_device_offset(self) -> None:
        bus = InMemoryTelemetryBus()
        e1 = TelemetryEvent("device-42", 1, {"reading_type": "gps", "value": 1.0}, datetime(2026, 1, 1, tzinfo=timezone.utc))
        e2 = TelemetryEvent("device-42", 2, {"reading_type": "gps", "value": 2.0}, datetime(2026, 1, 1, tzinfo=timezone.utc))
        e3 = TelemetryEvent("device-99", 1, {"reading_type": "gps", "value": 3.0}, datetime(2026, 1, 1, tzinfo=timezone.utc))

        o1 = bus.append("device-42", e1)
        o2 = bus.append("device-42", e2)
        o3 = bus.append("device-99", e3)

        self.assertEqual(o1, 1)
        self.assertEqual(o2, 2)
        self.assertEqual(o3, 1)

    def test_read_returns_per_device_events_in_order(self) -> None:
        bus = InMemoryTelemetryBus()
        events = [
            TelemetryEvent("device-42", i, {"reading_type": "gps", "value": float(i)}, datetime(2026, 1, 1, tzinfo=timezone.utc))
            for i in (1, 2, 3)
        ]
        for e in events:
            bus.append("device-42", e)

        read = bus.read("device-42", from_offset=1)
        self.assertEqual([e.sequence for e in read], [1, 2, 3])

    def test_read_from_offset(self) -> None:
        bus = InMemoryTelemetryBus()
        events = [
            TelemetryEvent("device-42", i, {"reading_type": "gps", "value": float(i)}, datetime(2026, 1, 1, tzinfo=timezone.utc))
            for i in (1, 2, 3)
        ]
        for e in events:
            bus.append("device-42", e)

        read = bus.read("device-42", from_offset=2)
        self.assertEqual([e.sequence for e in read], [2, 3])

    def test_read_unknown_device_empty(self) -> None:
        bus = InMemoryTelemetryBus()
        self.assertEqual(bus.read("device-999", from_offset=1), [])


class TelemetryIngestionTest(unittest.TestCase):
    def _make_service(self) -> TelemetryIngestion:
        return TelemetryIngestion(
            bus=InMemoryTelemetryBus(),
            schema=JsonSchemaAdapter(),
            clock=_FixedNow(datetime(2026, 1, 1, tzinfo=timezone.utc)),
        )

    def test_ingest_valid_event_accepted(self) -> None:
        service = self._make_service()
        result = service.ingest(
            IngestTelemetryCommand(
                device_id="device-42",
                sequence=1,
                payload={"reading_type": "gps", "value": 1.5},
            )
        )
        self.assertTrue(result.accepted)
        self.assertEqual(result.offset, 1)
        self.assertEqual(result.device_id, "device-42")
        self.assertEqual(result.sequence, 1)
        self.assertIn("device-42|1|", result.event_id)

    def test_ingest_invalid_schema_rejected_not_persisted(self) -> None:
        service = self._make_service()
        with self.assertRaises(InvalidSchemaError):
            service.ingest(
                IngestTelemetryCommand(
                    device_id="device-42",
                    sequence=1,
                    payload={"reading_type": "gps"},  # missing value
                )
            )
        # nothing persisted: reading again yields nothing
        self.assertEqual(service._bus.read("device-42", from_offset=1), [])

    def test_ingest_is_stateless_any_device_accepted(self) -> None:
        service = self._make_service()
        service.ingest(IngestTelemetryCommand("device-42", 1, {"reading_type": "gps", "value": 1.0}))
        service.ingest(IngestTelemetryCommand("device-99", 1, {"reading_type": "gps", "value": 2.0}))
        # both devices have offset 1 — no cross-device state
        self.assertEqual(len(service._bus.read("device-42", 1)), 1)
        self.assertEqual(len(service._bus.read("device-99", 1)), 1)

    def test_uses_fixed_clock_when_no_timestamp(self) -> None:
        service = self._make_service()
        result = service.ingest(
            IngestTelemetryCommand(
                device_id="device-42",
                sequence=1,
                payload={"reading_type": "gps", "value": 1.5},
            )
        )
        self.assertEqual(result.event_id, "device-42|1|2026-01-01T00:00:00+00:00")


if __name__ == "__main__":
    unittest.main()
