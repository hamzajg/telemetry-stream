"""Wave 2 integration tests — real Kafka (Redpanda) stream consumer.

Proves: per-device ordering via partition key, stateless multi-instance
consumption, projection state correctness. Requires Redpanda at
localhost:9092 (started for this wave). Skipped if no bus.

Each test class uses a unique topic + consumer group so events never leak
between runs. Separated from tests/unit/ because they require aiokafka and
a live Kafka cluster.
"""

from __future__ import annotations

import asyncio
import json
import socket
import subprocess
import time
import uuid
import unittest
from datetime import datetime, timezone

from aiokafka import AIOKafkaProducer

from telemetry.stream.domain.model import ProjectTelemetry
from telemetry.stream.domain.ports import Clock, TelemetryProjection, TelemetrySchema
from telemetry.stream.infrastructure.fixed_clock import FixedClock
from telemetry.stream.infrastructure.in_memory_projection import InMemoryTelemetryProjection
from telemetry.stream.infrastructure.json_schema_adapter import JsonSchemaAdapter
from telemetry.stream.infrastructure.kafka_consumer_adapter import KafkaStreamConsumer

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
    _rpk("topic", "delete", name)
    time.sleep(0.5)
    _rpk("topic", "create", name, "--partitions", "3", "--replicas", "1")
    time.sleep(1)


def _topic_name(suffix: str) -> str:
    return f"telemetry-stream-int-{suffix}-{uuid.uuid4().hex[:8]}"


def _make_processor() -> ProjectTelemetry:
    return ProjectTelemetry(
        projection=InMemoryTelemetryProjection(),
        schema=JsonSchemaAdapter(),
        clock=FixedClock(datetime(2026, 1, 1, tzinfo=timezone.utc)),
    )


@unittest.skipUnless(_bus_available(), "no Kafka bus at localhost:9092")
class KafkaStreamOrderingTest(unittest.TestCase):
    """Per-device ordering: key=device_id -> same partition -> emission order."""

    topic = _topic_name("ordering")
    group = f"test-ordering-{uuid.uuid4().hex[:8]}"

    @classmethod
    def setUpClass(cls):
        _create_topic(cls.topic)

    def _produce(self, device_id: str, sequence: int, reading: dict) -> None:
        async def _aproduce():
            producer = AIOKafkaProducer(bootstrap_servers=KAFKA_BOOTSTRAP)
            await producer.start()
            try:
                await producer.send_and_wait(
                    self.topic,
                    value=json.dumps(
                        {
                            "device_id": device_id,
                            "sequence": sequence,
                            "payload": reading,
                        }
                    ).encode("utf-8"),
                    key=device_id.encode("utf-8"),
                )
            finally:
                await producer.stop()

        asyncio.run(_aproduce())

    def test_per_device_ordering_emission_order(self) -> None:
        device = "device-42"
        for seq in (1, 2, 3):
            self._produce(device, seq, {"reading_type": "gps", "value": float(seq)})

        processor = _make_processor()
        consumer = KafkaStreamConsumer(
            KAFKA_BOOTSTRAP, self.topic, self.group, processor
        )
        stats = asyncio.run(consumer.run_once())

        self.assertEqual(stats["total"], 3)
        self.assertEqual(stats["projected"], 3)

        state = processor._projection.get(device)
        self.assertIsNotNone(state)
        self.assertEqual(state.latest_sequence, 3)
        self.assertEqual(state.latest_reading, {"reading_type": "gps", "value": 3.0})


@unittest.skipUnless(_bus_available(), "no Kafka bus at localhost:9092")
class KafkaStreamStatelessTest(unittest.TestCase):
    """Stateless: any consumer instance can consume any device's events."""

    topic = _topic_name("stateless")
    group = f"test-stateless-{uuid.uuid4().hex[:8]}"

    @classmethod
    def setUpClass(cls):
        _create_topic(cls.topic)

    def _produce(self, device_id: str, sequence: int, reading: dict) -> None:
        async def _aproduce():
            producer = AIOKafkaProducer(bootstrap_servers=KAFKA_BOOTSTRAP)
            await producer.start()
            try:
                await producer.send_and_wait(
                    self.topic,
                    value=json.dumps(
                        {
                            "device_id": device_id,
                            "sequence": sequence,
                            "payload": reading,
                        }
                    ).encode("utf-8"),
                    key=device_id.encode("utf-8"),
                )
            finally:
                await producer.stop()

        asyncio.run(_aproduce())

    def test_two_instances_consume_same_device(self) -> None:
        device = "device-99"
        self._produce(device, 1, {"reading_type": "gps", "value": 1.0})
        self._produce(device, 2, {"reading_type": "gps", "value": 2.0})

        processor_a = _make_processor()
        consumer_a = KafkaStreamConsumer(
            KAFKA_BOOTSTRAP, self.topic, self.group, processor_a
        )
        stats_a = asyncio.run(consumer_a.run_once())

        # Second instance with same group would get no new messages (committed).
        # Use a different group to prove any instance can consume any device.
        group_b = f"test-stateless-b-{uuid.uuid4().hex[:8]}"
        processor_b = _make_processor()
        consumer_b = KafkaStreamConsumer(
            KAFKA_BOOTSTRAP, self.topic, group_b, processor_b
        )
        stats_b = asyncio.run(consumer_b.run_once())

        self.assertEqual(stats_a["projected"], 2)
        self.assertEqual(stats_b["projected"], 2)

        state_a = processor_a._projection.get(device)
        state_b = processor_b._projection.get(device)
        self.assertIsNotNone(state_a)
        self.assertIsNotNone(state_b)
        self.assertEqual(state_a.latest_sequence, 2)
        self.assertEqual(state_b.latest_sequence, 2)


@unittest.skipUnless(_bus_available(), "no Kafka bus at localhost:9092")
class KafkaStreamRejectTest(unittest.TestCase):
    """Invalid schema events are skipped and not projected, error counted."""

    topic = _topic_name("reject")
    group = f"test-reject-{uuid.uuid4().hex[:8]}"

    @classmethod
    def setUpClass(cls):
        _create_topic(cls.topic)

    def _produce(self, device_id: str, sequence: int, payload: dict) -> None:
        async def _aproduce():
            producer = AIOKafkaProducer(bootstrap_servers=KAFKA_BOOTSTRAP)
            await producer.start()
            try:
                await producer.send_and_wait(
                    self.topic,
                    value=json.dumps(
                        {
                            "device_id": device_id,
                            "sequence": sequence,
                            "payload": payload,
                        }
                    ).encode("utf-8"),
                    key=device_id.encode("utf-8"),
                )
            finally:
                await producer.stop()

        asyncio.run(_aproduce())

    def test_invalid_schema_skipped_not_projected(self) -> None:
        device = "device-42"
        self._produce(device, 1, {"reading_type": "gps"})  # missing value

        processor = _make_processor()
        consumer = KafkaStreamConsumer(
            KAFKA_BOOTSTRAP, self.topic, self.group, processor
        )
        stats = asyncio.run(consumer.run_once())

        self.assertEqual(stats["total"], 1)
        # Invalid schema raises -> counted as error, not projected
        self.assertEqual(stats["errors"], 1)
        self.assertEqual(stats["projected"], 0)

        state = processor._projection.get(device)
        self.assertIsNone(state)


if __name__ == "__main__":
    unittest.main()
