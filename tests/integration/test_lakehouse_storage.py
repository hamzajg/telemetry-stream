"""Wave 2 integration tests — real object storage (local filesystem adapter
through the full domain service path), proving idempotent writes and
stateless multi-instance consumption.

Proves: AC2 (idempotent writes keyed by device_id + offset), AC4 (stateless
writer — any instance writes any device). Separated from tests/unit/ because
they exercise the full storage + catalog adapter stack.
"""

from __future__ import annotations

import tempfile
import unittest
from datetime import datetime, timezone

from telemetry.lakehouse.domain.model import (
    WriteTelemetry,
    WriteTelemetryCommand,
)
from telemetry.lakehouse.domain.ports import Clock
from telemetry.lakehouse.infrastructure.fixed_clock import FixedClock
from telemetry.lakehouse.infrastructure.local_catalog import LocalLakehouseCatalog
from telemetry.lakehouse.infrastructure.local_storage import LocalLakehouseStorage


class _FixedNow(Clock):
    def __init__(self, instant: datetime) -> None:
        self._instant = instant

    def now(self) -> datetime:
        return self._instant


class LakehouseIdempotencyTest(unittest.TestCase):
    """Idempotent writes: same device_id + offset written twice = one row."""

    def test_same_offset_written_twice_is_one_row(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            storage = LocalLakehouseStorage(tmp)
            catalog = LocalLakehouseCatalog()
            clock = _FixedNow(datetime(2026, 1, 15, tzinfo=timezone.utc))
            service = WriteTelemetry(storage, catalog, clock)

            cmd = WriteTelemetryCommand(
                device_id="device-42",
                sequence=1,
                offset=10,
                event_date="2026-01-15",
                payload={"reading_type": "gps", "value": 1.5},
            )

            r1 = service.write(cmd)
            r2 = service.write(cmd)

            self.assertTrue(r1.written)
            self.assertFalse(r2.written)  # duplicate — skipped

            # Exactly one row on disk
            partition = "device_id=device-42/event_date=2026-01-15/"
            self.assertTrue(storage.exists(partition, r1.row_key))
            self.assertEqual(len(storage._written), 1)


class LakehouseStatelessTest(unittest.TestCase):
    """Stateless writer: any instance can write any device's events."""

    def test_two_instances_write_same_device(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            storage = LocalLakehouseStorage(tmp)
            catalog = LocalLakehouseCatalog()
            clock = _FixedNow(datetime(2026, 1, 15, tzinfo=timezone.utc))

            service_a = WriteTelemetry(storage, catalog, clock)
            service_b = WriteTelemetry(storage, catalog, clock)

            # Both services share the same storage (no device pinning)
            r1 = service_a.write(
                WriteTelemetryCommand(
                    device_id="device-42",
                    sequence=1,
                    offset=10,
                    event_date="2026-01-15",
                    payload={"reading_type": "gps", "value": 1.0},
                )
            )
            r2 = service_b.write(
                WriteTelemetryCommand(
                    device_id="device-42",
                    sequence=2,
                    offset=11,
                    event_date="2026-01-15",
                    payload={"reading_type": "gps", "value": 2.0},
                )
            )

            self.assertTrue(r1.written)
            self.assertTrue(r2.written)
            # Two distinct rows for the same device — no writer pinning
            self.assertEqual(len(storage._written), 2)

            partition = "device_id=device-42/event_date=2026-01-15/"
            self.assertTrue(storage.exists(partition, r1.row_key))
            self.assertTrue(storage.exists(partition, r2.row_key))


if __name__ == "__main__":
    unittest.main()
