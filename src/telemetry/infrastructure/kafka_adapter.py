"""Kafka adapter implementing the TelemetryBus port.

Uses aiokafka internally with an asyncio bridge so the sync port methods
(append/read) can be called from the sync domain core. device_id is the
Kafka partition key, so all events for a device land in the same partition
in emission order (per-device ordering). The returned Kafka offset is the
replayable cursor.

Tests use InMemoryTelemetryBus instead; this adapter is wired for production
against a live Kafka cluster.
"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from typing import List

from aiokafka import AIOKafkaConsumer, AIOKafkaProducer

from telemetry.domain.model import TelemetryEvent
from telemetry.domain.ports import TelemetryBus


def _event_to_json(event: TelemetryEvent) -> bytes:
    return json.dumps(
        {
            "device_id": event.device_id,
            "sequence": event.sequence,
            "payload": event.payload,
            "timestamp": event.timestamp.isoformat(),
            "event_id": event.event_id,
        }
    ).encode("utf-8")


def _json_to_event(value: bytes) -> TelemetryEvent:
    data = json.loads(value)
    ts = data["timestamp"]
    if ts.endswith("Z"):
        ts = ts[:-1] + "+00:00"
    return TelemetryEvent(
        device_id=data["device_id"],
        sequence=data["sequence"],
        payload=data["payload"],
        timestamp=datetime.fromisoformat(ts),
    )


class KafkaTelemetryBus(TelemetryBus):
    """Kafka-backed durable event bus.

    device_id is the message key -> same partition per device -> ordered.
    Kafka offset is the replayable cursor.
    """

    def __init__(self, bootstrap_servers: str, topic: str) -> None:
        self._bootstrap_servers = bootstrap_servers
        self._topic = topic

    def append(self, device_id: str, event: TelemetryEvent) -> int:
        loop = asyncio.new_event_loop()
        try:
            metadata = loop.run_until_complete(self._aproduce_once(device_id, event))
            return metadata.offset
        finally:
            loop.close()

    async def _aproduce_once(self, device_id: str, event: TelemetryEvent):
        producer = AIOKafkaProducer(bootstrap_servers=self._bootstrap_servers)
        await producer.start()
        try:
            return await self._producer_send(producer, device_id, event)
        finally:
            await producer.stop()

    async def _producer_send(
        self, producer: AIOKafkaProducer, device_id: str, event: TelemetryEvent
    ):
        return await producer.send_and_wait(
            self._topic,
            value=_event_to_json(event),
            key=device_id.encode("utf-8"),
        )

    def read(self, device_id: str, from_offset: int) -> List[TelemetryEvent]:
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(self._aread_once(device_id, from_offset))
        finally:
            loop.close()

    async def _aread_once(self, device_id: str, from_offset: int) -> List[TelemetryEvent]:
        consumer = AIOKafkaConsumer(
            bootstrap_servers=self._bootstrap_servers,
            auto_offset_reset="earliest",
            enable_auto_commit=False,
            group_id="telemetry-ingestion-reader",
        )
        await consumer.start()
        try:
            consumer.subscribe([self._topic])
            # Wait for partition assignment (rebalance).
            for _ in range(50):
                if consumer.assignment():
                    break
                await asyncio.sleep(0.1)

            results: List[TelemetryEvent] = []
            key = device_id.encode("utf-8")
            while True:
                batch = await consumer.getmany(timeout_ms=3000, max_records=500)
                if not batch:
                    break
                for _tp, messages in batch.items():
                    for msg in messages:
                        if msg.key != key:
                            continue
                        if msg.offset < from_offset:
                            continue
                        results.append(_json_to_event(msg.value))
            return results
        finally:
            await consumer.stop()
