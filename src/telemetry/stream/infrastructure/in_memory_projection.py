"""In-memory test double for the TelemetryProjection port.

Pure Python, no database. Used by domain/core tests so they run without a
projection store. Not used in production.
"""

from __future__ import annotations

from typing import Dict

from telemetry.stream.domain.model import DeviceState
from telemetry.stream.domain.ports import TelemetryProjection


class InMemoryTelemetryProjection(TelemetryProjection):
    """In-memory current-device-state store keyed by device_id."""

    def __init__(self) -> None:
        self._states: Dict[str, DeviceState] = {}

    def get(self, device_id: str) -> DeviceState | None:
        return self._states.get(device_id)

    def save(self, device_id: str, state: DeviceState) -> None:
        self._states[device_id] = state
