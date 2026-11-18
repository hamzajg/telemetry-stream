"""Stream processing domain core tests — pure Python, no Kafka, no Spark, no DB.

These run against in-memory doubles implementing the ports, proving the
domain is independently testable (hexagonal: policy depends on nothing).
"""

from __future__ import annotations

import unittest
from datetime import datetime, timezone

from telemetry.stream.domain.model import (
    DeviceState,
    InvalidSchemaError,
    OutOfOrderEventError,
    ProjectTelemetryCommand,
    ProjectTelemetryResult,
    ProjectTelemetry,
)
from telemetry.stream.domain.ports import Clock, TelemetryProjection, TelemetrySchema
from telemetry.stream.infrastructure.fixed_clock import FixedClock
from telemetry.stream.infrastructure.in_memory_projection import InMemoryTelemetryProjection
from telemetry.stream.infrastructure.json_schema_adapter import JsonSchemaAdapter


class _FixedNow(Clock):
    def __init__(self, instant: datetime) -> None:
        self._instant = instant

    def now(self) -> datetime:
        return self._instant


class DeviceStateTest(unittest.TestCase):
    def test_initial_state(self) -> None:
        state = DeviceState.initial("device-42")
        self.assertEqual(state.device_id, "device-42")
        self.assertEqual(state.latest_sequence, 0)
        self.assertEqual(state.latest_reading, {})

    def test_is_newer_advances(self) -> None:
        state = DeviceState.initial("device-42")
        self.assertTrue(state.is_newer(1))
        self.assertFalse(state.is_newer(0))
        advanced = state.advance(1, {"reading_type": "gps", "value": 1.0}, datetime(2026, 1, 1, tzinfo=timezone.utc))
        self.assertFalse(advanced.is_newer(1))  # equal, not newer

    def test_advance_is_immutable(self) -> None:
        state = DeviceState.initial("device-42")
        new = state.advance(1, {"reading_type": "gps", "value": 1.5}, datetime(2026, 1, 1, tzinfo=timezone.utc))
        self.assertEqual(state.latest_sequence, 0)  # original unchanged
        self.assertEqual(new.latest_sequence, 1)
        self.assertEqual(new.latest_reading, {"reading_type": "gps", "value": 1.5})


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


class InMemoryProjectionTest(unittest.TestCase):
    def test_get_unknown_device_returns_none(self) -> None:
        store = InMemoryTelemetryProjection()
        self.assertIsNone(store.get("device-999"))

    def test_save_and_get(self) -> None:
        store = InMemoryTelemetryProjection()
        state = DeviceState.initial("device-42")
        store.save("device-42", state)
        self.assertEqual(store.get("device-42"), state)


class ProjectTelemetryTest(unittest.TestCase):
    def _make_service(self) -> ProjectTelemetry:
        return ProjectTelemetry(
            projection=InMemoryTelemetryProjection(),
            schema=JsonSchemaAdapter(),
            clock=_FixedNow(datetime(2026, 1, 1, tzinfo=timezone.utc)),
        )

    # Scenario: consumed telemetry event updates current device state
    def test_project_valid_event_advances_state(self) -> None:
        service = self._make_service()
        result = service.project(
            ProjectTelemetryCommand(
                device_id="device-42",
                sequence=1,
                payload={"reading_type": "gps", "value": 1.5},
                offset=10,
            )
        )
        self.assertTrue(result.projected)
        self.assertEqual(result.sequence, 1)
        self.assertEqual(result.offset, 10)

        state = service._projection.get("device-42")
        self.assertIsNotNone(state)
        self.assertEqual(state.latest_sequence, 1)
        self.assertEqual(state.latest_reading, {"reading_type": "gps", "value": 1.5})

    def test_project_duplicate_sequence_is_skipped(self) -> None:
        service = self._make_service()
        service.project(
            ProjectTelemetryCommand(
                device_id="device-42",
                sequence=1,
                payload={"reading_type": "gps", "value": 1.5},
                offset=10,
            )
        )
        result = service.project(
            ProjectTelemetryCommand(
                device_id="device-42",
                sequence=1,
                payload={"reading_type": "gps", "value": 2.0},
                offset=11,
            )
        )
        self.assertFalse(result.projected)
        state = service._projection.get("device-42")
        self.assertEqual(state.latest_sequence, 1)
        self.assertEqual(state.latest_reading, {"reading_type": "gps", "value": 1.5})

    # Scenario: consumer reads events in per-device emission order from Kafka
    def test_project_out_of_order_is_skipped(self) -> None:
        service = self._make_service()
        service.project(
            ProjectTelemetryCommand(
                device_id="device-42",
                sequence=3,
                payload={"reading_type": "gps", "value": 3.0},
                offset=10,
            )
        )
        result = service.project(
            ProjectTelemetryCommand(
                device_id="device-42",
                sequence=2,
                payload={"reading_type": "gps", "value": 2.0},
                offset=11,
            )
        )
        self.assertFalse(result.projected)
        state = service._projection.get("device-42")
        self.assertEqual(state.latest_sequence, 3)

    def test_project_invalid_schema_rejected_not_projected(self) -> None:
        service = self._make_service()
        with self.assertRaises(InvalidSchemaError):
            service.project(
                ProjectTelemetryCommand(
                    device_id="device-42",
                    sequence=1,
                    payload={"reading_type": "gps"},  # missing value
                    offset=10,
                )
            )
        # nothing projected
        self.assertIsNone(service._projection.get("device-42"))

    def test_project_is_stateless_per_device(self) -> None:
        service = self._make_service()
        service.project(
            ProjectTelemetryCommand(
                device_id="device-42",
                sequence=1,
                payload={"reading_type": "gps", "value": 1.0},
                offset=10,
            )
        )
        service.project(
            ProjectTelemetryCommand(
                device_id="device-99",
                sequence=1,
                payload={"reading_type": "gps", "value": 2.0},
                offset=11,
            )
        )
        # both devices have sequence 1 — no cross-device state
        self.assertEqual(service._projection.get("device-42").latest_sequence, 1)
        self.assertEqual(service._projection.get("device-99").latest_sequence, 1)


if __name__ == "__main__":
    unittest.main()
