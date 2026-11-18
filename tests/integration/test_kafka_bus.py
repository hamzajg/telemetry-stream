"""Wave 2 integration tests — real Kafka (Redpanda) bus.

Proves: per-device ordering via partition key, stateless multi-instance
acceptance, replay from a Kafka offset. Requires a running Kafka-compatible
bus at localhost:9092 (Redpanda started for this wave). Skipped if no bus.

Each test class uses a unique topic so events never leak between runs.
These are separated from tests/unit/test_domain.py (stdlib-only) because
they require aiokafka and a live Kafka cluster.
"""

from __future__ import annotations

import socket
import subprocess
import time
import uuid
import unittest
from datetime import datetime, timezone

from telemetry.domain.model import IngestTelemetryCommand, TelemetryIngestion
from telemetry.domain.exceptions import InvalidSchemaError
from telemetry.domain.ports import TelemetrySchema
from telemetry.infrastructure.json_schema_adapter import JsonSchemaAdapter
from telemetry.infrastructure.kafka_adapter import KafkaTelemetryBus
from telemetry.infrastructure.fixed_clock import FixedClock

KAFKA_BOOTSTRAP = "localhost:9092"


def _bus_available() -> bool:
    s = socket.socket()
    s.settimeout(2)
    try:
        s.connect(("localhost", 9092))
        return True
    except OSError:
        return False
    finally:
        s.close()


def _rpk(*args):
    return subprocess.run(
        ["docker", "exec", "telemetry-redpanda", "rpk", *args],
        capture_output=True, text=True, timeout=30,
    )


def _create_topic(name: str) -> None:
    _rpk("topic", "delete", name)  # ignore if missing
    time.sleep(0.5)
    _rpk("topic", "create", name, "--partitions", "3", "--replicas", "1")
    time.sleep(1)


def _topic_name(suffix: str) -> str:
    return f"telemetry-int-{suffix}-{uuid.uuid4().hex[:8]}"


@unittest.skipUnless(_bus_available(), "no Kafka bus at localhost:9092")
class KafkaOrderingTest(unittest.TestCase):
    """Per-device ordering: key=device_id -> same partition -> emission order."""

    topic = _topic_name("ordering")

    @classmethod
    def setUpClass(cls):
        _create_topic(cls.topic)

    def setUp(self) -> None:
        self.bus = KafkaTelemetryBus(KAFKA_BOOTSTRAP, self.topic)
        self.schema = JsonSchemaAdapter()
        self.clock = FixedClock(datetime(2026, 1, 1, tzinfo=timezone.utc))
        self.ingestion = TelemetryIngestion(self.bus, self.schema, self.clock)

    def _payload(self, seq: int) -> dict:
        return {"reading_type": "gps", "value": float(seq), "seq": seq}

    def test_per_device_ordering_emission_order(self) -> None:
        device = "device-42"
        offsets = []
        for seq in (1, 2, 3):
            result = self.ingestion.ingest(
                IngestTelemetryCommand(device, seq, self._payload(seq))
            )
            self.assertTrue(result.accepted)
            offsets.append(result.offset)

        # Offsets must be strictly increasing (ordered within the partition).
        self.assertEqual(offsets, sorted(offsets))
        self.assertEqual(len(set(offsets)), 3)

        # Replay from the first offset returns all three in order.
        events = self.bus.read(device, from_offset=offsets[0])
        self.assertEqual([e.sequence for e in events], [1, 2, 3])

    def test_replay_from_middle_offset(self) -> None:
        device = "device-42"
        offsets = []
        for seq in (1, 2, 3):
            result = self.ingestion.ingest(
                IngestTelemetryCommand(device, seq, self._payload(seq))
            )
            offsets.append(result.offset)

        # Read from offset 2 -> should get sequences 2, 3.
        events = self.bus.read(device, from_offset=offsets[1])
        self.assertEqual([e.sequence for e in events], [2, 3])


@unittest.skipUnless(_bus_available(), "no Kafka bus at localhost:9092")
class KafkaStatelessTest(unittest.TestCase):
    """Stateless: any ingestion instance can accept events for any device."""

    topic = _topic_name("stateless")

    @classmethod
    def setUpClass(cls):
        _create_topic(cls.topic)

    def setUp(self) -> None:
        self.schema = JsonSchemaAdapter()
        self.clock = FixedClock(datetime(2026, 1, 1, tzinfo=timezone.utc))

    def _payload(self, seq: int) -> dict:
        return {"reading_type": "gps", "value": float(seq), "seq": seq}

    def test_two_instances_accept_same_device(self) -> None:
        device = "device-99"
        instance_a = TelemetryIngestion(
            KafkaTelemetryBus(KAFKA_BOOTSTRAP, self.topic),
            self.schema,
            self.clock,
        )
        instance_b = TelemetryIngestion(
            KafkaTelemetryBus(KAFKA_BOOTSTRAP, self.topic),
            self.schema,
            self.clock,
        )

        r1 = instance_a.ingest(IngestTelemetryCommand(device, 1, self._payload(1)))
        r2 = instance_b.ingest(IngestTelemetryCommand(device, 2, self._payload(2)))
        self.assertTrue(r1.accepted)
        self.assertTrue(r2.accepted)
        # Both instances accepted events for the same device -> no pinning.
        self.assertNotEqual(r1.event_id, r2.event_id)


@unittest.skipUnless(_bus_available(), "no Kafka bus at localhost:9092")
class KafkaRejectTest(unittest.TestCase):
    """Invalid schema events are rejected and not persisted to the bus."""

    topic = _topic_name("reject")

    @classmethod
    def setUpClass(cls):
        _create_topic(cls.topic)

    def setUp(self) -> None:
        self.bus = KafkaTelemetryBus(KAFKA_BOOTSTRAP, self.topic)
        self.schema = JsonSchemaAdapter()
        self.clock = FixedClock(datetime(2026, 1, 1, tzinfo=timezone.utc))
        self.ingestion = TelemetryIngestion(self.bus, self.schema, self.clock)

    def test_invalid_schema_not_persisted(self) -> None:
        device = "device-42"
        with self.assertRaises(InvalidSchemaError):
            self.ingestion.ingest(
                IngestTelemetryCommand(device, 1, {"reading_type": "gps"})  # missing value
            )
        # Nothing persisted for this device on this fresh topic.
        self.assertEqual(self.bus.read(device, from_offset=0), [])


if __name__ == "__main__":
    unittest.main()
