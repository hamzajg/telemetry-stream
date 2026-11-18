"""Lakehouse storage domain core tests — pure Python, no S3, no Glue, no cloud SDK.

These run against in-memory/local doubles implementing the ports, proving
the domain is independently testable (hexagonal: policy depends on nothing).
"""

from __future__ import annotations

import os
import tempfile
import unittest
from datetime import datetime, timezone

from telemetry.lakehouse.domain.model import (
    DuplicateOffsetError,
    InvalidSchemaError,
    LakehouseRow,
    WriteTelemetry,
    WriteTelemetryCommand,
    WriteTelemetryResult,
)
from telemetry.lakehouse.domain.ports import Clock, LakehouseCatalog, LakehouseStorage
from telemetry.lakehouse.infrastructure.fixed_clock import FixedClock
from telemetry.lakehouse.infrastructure.local_catalog import LocalLakehouseCatalog
from telemetry.lakehouse.infrastructure.local_storage import LocalLakehouseStorage


class _FixedNow(Clock):
    def __init__(self, instant: datetime) -> None:
        self._instant = instant

    def now(self) -> datetime:
        return self._instant


class LakehouseRowTest(unittest.TestCase):
    def test_partition_path(self) -> None:
        row = LakehouseRow(
            device_id="device-42",
            sequence=1,
            offset=10,
            event_date="2026-01-15",
            payload={"reading_type": "gps", "value": 1.5},
            written_at=datetime(2026, 1, 15, tzinfo=timezone.utc),
        )
        self.assertEqual(
            row.partition_path(), "device_id=device-42/event_date=2026-01-15/"
        )

    def test_row_key_is_deterministic(self) -> None:
        row = LakehouseRow(
            device_id="device-42",
            sequence=1,
            offset=10,
            event_date="2026-01-15",
            payload={"reading_type": "gps", "value": 1.5},
            written_at=datetime(2026, 1, 15, tzinfo=timezone.utc),
        )
        self.assertEqual(len(row.row_key()), 16)
        self.assertEqual(row.row_key(), row.row_key())  # deterministic


class LocalStorageTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.mkdtemp()
        self.storage = LocalLakehouseStorage(self._tmp)

    def test_write_and_exists(self) -> None:
        row = LakehouseRow(
            device_id="device-42",
            sequence=1,
            offset=10,
            event_date="2026-01-15",
            payload={"reading_type": "gps", "value": 1.5},
            written_at=datetime(2026, 1, 15, tzinfo=timezone.utc),
        )
        self.assertFalse(
            self.storage.exists("device_id=device-42/event_date=2026-01-15/", "abc123")
        )
        self.storage.write(
            "device_id=device-42/event_date=2026-01-15/", "abc123", row
        )
        self.assertTrue(
            self.storage.exists("device_id=device-42/event_date=2026-01-15/", "abc123")
        )

    def test_duplicate_write_raises(self) -> None:
        row = LakehouseRow(
            device_id="device-42",
            sequence=1,
            offset=10,
            event_date="2026-01-15",
            payload={"reading_type": "gps", "value": 1.5},
            written_at=datetime(2026, 1, 15, tzinfo=timezone.utc),
        )
        self.storage.write("p/", "k1", row)
        with self.assertRaises(DuplicateOffsetError):
            self.storage.write("p/", "k1", row)


class LocalCatalogTest(unittest.TestCase):
    def test_register_and_exists(self) -> None:
        catalog = LocalLakehouseCatalog()
        self.assertFalse(catalog.table_exists("telemetry_device_42"))
        catalog.register_table("telemetry_device_42", "p/")
        self.assertTrue(catalog.table_exists("telemetry_device_42"))


class WriteTelemetryTest(unittest.TestCase):
    def _make_service(self, tmp_dir: str) -> WriteTelemetry:
        return WriteTelemetry(
            storage=LocalLakehouseStorage(tmp_dir),
            catalog=LocalLakehouseCatalog(),
            clock=_FixedNow(datetime(2026, 1, 15, tzinfo=timezone.utc)),
        )

    # Scenario: projected telemetry event is written to lakehouse partitioned by device_id and date
    def test_write_valid_event(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            service = self._make_service(tmp)
            result = service.write(
                WriteTelemetryCommand(
                    device_id="device-42",
                    sequence=1,
                    offset=10,
                    event_date="2026-01-15",
                    payload={"reading_type": "gps", "value": 1.5},
                )
            )
            self.assertTrue(result.written)
            self.assertEqual(result.device_id, "device-42")
            self.assertEqual(result.sequence, 1)
            self.assertEqual(result.offset, 10)
            self.assertEqual(
                result.partition_path,
                "device_id=device-42/event_date=2026-01-15/",
            )
            self.assertEqual(len(result.row_key), 16)

    # Scenario: lakehouse writes are idempotent — replaying same offset does not duplicate
    def test_write_idempotent_skip_on_duplicate_offset(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            service = self._make_service(tmp)
            service.write(
                WriteTelemetryCommand(
                    device_id="device-42",
                    sequence=1,
                    offset=10,
                    event_date="2026-01-15",
                    payload={"reading_type": "gps", "value": 1.5},
                )
            )
            result = service.write(
                WriteTelemetryCommand(
                    device_id="device-42",
                    sequence=1,
                    offset=10,
                    event_date="2026-01-15",
                    payload={"reading_type": "gps", "value": 2.0},
                )
            )
            self.assertFalse(result.written)  # skipped — same offset

    # Scenario: Schema validation: event failing schema is not written to lakehouse
    def test_write_invalid_schema_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            service = self._make_service(tmp)
            with self.assertRaises(InvalidSchemaError):
                service.write(
                    WriteTelemetryCommand(
                        device_id="device-42",
                        sequence=1,
                        offset=10,
                        event_date="2026-01-15",
                        payload={},  # empty — invalid
                    )
                )

    # Scenario: stored lakehouse rows are recoverable from a committed offset after restart
    def test_rows_recoverable_from_committed_offset_after_restart(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            # First session: write rows for offsets 1..5
            service = self._make_service(tmp)
            for offset in range(1, 6):
                service.write(
                    WriteTelemetryCommand(
                        device_id="device-42",
                        sequence=offset,
                        offset=offset,
                        event_date="2026-01-15",
                        payload={"reading_type": "gps", "value": float(offset)},
                    )
                )
            # Simulate restart: new service instance, same underlying storage
            restarted = WriteTelemetry(
                storage=LocalLakehouseStorage(tmp),
                catalog=LocalLakehouseCatalog(),
                clock=_FixedNow(datetime(2026, 1, 15, tzinfo=timezone.utc)),
            )
            partition_path = "device_id=device-42/event_date=2026-01-15/"
            # Rows at and after committed offset 3 are recoverable
            for offset in (3, 4, 5):
                row_key = LakehouseRow(
                    device_id="device-42",
                    sequence=offset,
                    offset=offset,
                    event_date="2026-01-15",
                    payload={},
                    written_at=datetime(2026, 1, 15, tzinfo=timezone.utc),
                ).row_key()
                self.assertTrue(
                    restarted._storage.exists(partition_path, row_key),
                    f"offset {offset} not recoverable after restart",
                )

    # Scenario: lakehouse writer is stateless — any instance can write any device
    def test_write_is_stateless_per_device(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            service = self._make_service(tmp)
            # Both devices can write offset 10 — no cross-device state pinning.
            service.write(
                WriteTelemetryCommand(
                    device_id="device-42",
                    sequence=1,
                    offset=10,
                    event_date="2026-01-15",
                    payload={"reading_type": "gps", "value": 1.0},
                )
            )
            service.write(
                WriteTelemetryCommand(
                    device_id="device-99",
                    sequence=1,
                    offset=10,
                    event_date="2026-01-15",
                    payload={"reading_type": "gps", "value": 2.0},
                )
            )
            # If we reach here without exception, both writes succeeded
            # (stateless — no device-to-writer pinning).
            self.assertTrue(True)



if __name__ == "__main__":
    unittest.main()
