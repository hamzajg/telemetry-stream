"""In-memory test double for the DeviceRegistry port.

Pure Python, no database. Used by domain/core tests so they run without a
registry. Not used in production.
"""

from __future__ import annotations

from typing import Dict

from telemetry.device.domain.model import (
    Credential,
    Device,
    DeviceAlreadyRegisteredError,
)
from telemetry.device.domain.ports import DeviceRegistry


class InMemoryDeviceRegistry(DeviceRegistry):
    """In-memory device registry keyed by device_id."""

    def __init__(self) -> None:
        self._devices: Dict[str, Device] = {}

    def get(self, device_id: str) -> Device | None:
        return self._devices.get(device_id)

    def save(self, device: Device) -> None:
        if device.device_id in self._devices:
            raise DeviceAlreadyRegisteredError(
                f"device {device.device_id} already registered"
            )
        self._devices[device.device_id] = device

    def list_active(self) -> list[Device]:
        return [d for d in self._devices.values() if d.active]


class InMemoryCredentialStore:
    """In-memory credential store keyed by credential_id.

    Used by domain/core tests so they run without a secret manager.
    Not used in production.
    """

    def __init__(self) -> None:
        self._credentials: Dict[str, Credential] = {}

    def get(self, credential_id: str) -> Credential | None:
        return self._credentials.get(credential_id)

    def save(self, credential: Credential) -> None:
        self._credentials[credential.credential_id] = credential
