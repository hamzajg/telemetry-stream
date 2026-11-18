"""Kafka streaming consumer adapter implementing the stream processing pipeline.

Reads telemetry events from Kafka (device_id as partition key -> per-device
ordering), validates and projects each event through the domain service, and
commits offsets. Stateless: any consumer instance can consume any partition.

Wires the Kafka read port to the ProjectTelemetry domain service.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from aiokafka import AIOKafkaConsumer

from telemetry.stream.domain.model import ProjectTelemetryCommand, ProjectTelemetry

logger = logging.getLogger("telemetry.stream.consumer")


def _parse_event(value: bytes) -> dict:
    return json.loads(value)


class KafkaStreamConsumer:
    """Stateless Kafka stream consumer that projects telemetry events.

    For each message: parse -> validate -> project -> commit offset.
    device_id is the message key, so all events for a device are consumed
    in order from the same partition (per-device ordering).
    """

    def __init__(
        self,
        bootstrap_servers: str,
        topic: str,
        group_id: str,
        project_telemetry: ProjectTelemetry,
        consumer_timeout_ms: int = 5000,
        max_records: int = 500,
    ) -> None:
        self._bootstrap_servers = bootstrap_servers
        self._topic = topic
        self._group_id = group_id
        self._project_telemetry = project_telemetry
        self._consumer_timeout_ms = consumer_timeout_ms
        self._max_records = max_records

    async def run_once(self) -> dict[str, int]:
        """Consume one batch of messages and project them.

        Returns stats: {projected, skipped, errors, total}.
        """
        stats = {"projected": 0, "skipped": 0, "errors": 0, "total": 0}

        consumer = AIOKafkaConsumer(
            bootstrap_servers=self._bootstrap_servers,
            group_id=self._group_id,
            auto_offset_reset="earliest",
            enable_auto_commit=False,
        )
        await consumer.start()
        try:
            consumer.subscribe([self._topic])
            for _ in range(50):
                if consumer.assignment():
                    break
                await asyncio.sleep(0.1)

            while True:
                batch = await consumer.getmany(
                    timeout_ms=self._consumer_timeout_ms,
                    max_records=self._max_records,
                )
                if not batch:
                    break
                for _tp, messages in batch.items():
                    for msg in messages:
                        stats["total"] += 1
                        try:
                            await self._process_message(msg)
                            stats["projected"] += 1
                        except Exception as exc:  # noqa: BLE001
                            logger.error(
                                "Failed to project message offset %s: %s", msg.offset, exc
                            )
                            stats["errors"] += 1
                        finally:
                            # Commit per-message for at-least-once + idempotent dedup.
                            await consumer.commit()
        finally:
            await consumer.stop()

        return stats

    async def _process_message(self, msg: Any) -> None:
        """Parse, validate, and project a single Kafka message."""
        payload = _parse_event(msg.value)
        device_id = payload.get(
            "device_id", msg.key.decode("utf-8") if msg.key else "unknown"
        )
        sequence = int(payload.get("sequence", 0))
        reading = payload.get("payload", {})

        command = ProjectTelemetryCommand(
            device_id=device_id,
            sequence=sequence,
            payload=reading,
            offset=msg.offset,
            timestamp=None,  # domain clock supplies the time
        )

        result = self._project_telemetry.project(command)
        if not result.projected:
            # Duplicate or out-of-order — idempotent skip, still committed.
            pass
