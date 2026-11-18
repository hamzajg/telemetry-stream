"""Ports: interfaces the device domain depends on. Adapters implement these."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol, runtime_checkable

from telemetry.device.domain.model import Credential, Device


@runtime_checkable
class DeviceRegistry(Protocol):
    """Device registry store (e.g. in-memory dict, database)."""

    def get(self, device_id: str) -> Device | None:
        """Return the device for ``device_id``, or None if not registered."""

    def save(self, device: Device) -> None:
        """Persist ``device``.

        Raises DeviceAlreadyRegisteredError if the device already exists.
        """

    def list_active(self) -> list[Device]:
        """Return all active devices."""


@runtime_checkable
class CredentialStore(Protocol):
    """Credential store (e.g. env vars, secret manager)."""

    def get(self, credential_id: str) -> Credential | None:
        """Return the credential for ``credential_id``, or None if unknown."""

    def save(self, credential: Credential) -> None:
        """Persist ``credential`` (upsert: insert or replace by id)."""


@runtime_checkable
class Clock(Protocol):
    """Injectable time seam for deterministic tests."""

    def now(self) -> datetime:
        """Return the current UTC time."""
