"""Device management application layer tests — pure Python, no framework.

Tests the application use cases wrapping the domain service against
in-memory port doubles. Wave 2 scenarios:

- unregistered device is rejected and cannot produce telemetry
- revoked credential is rejected even if previously valid
- credential rotation invalidates old credential and activates new one
- device registry is queryable — active device count and registration details
"""

from __future__ import annotations

import unittest
from datetime import datetime, timezone

from telemetry.device.application.use_cases import (
    AuthorizeDeviceRequest,
    DeviceApplication,
    ProvisionCredentialRequest,
    RegisterDeviceRequest,
    RevokeCredentialRequest,
    RotateCredentialRequest,
)
from telemetry.device.domain.model import (
    Credential,
    Device,
    DeviceManagement,
    InvalidCredentialError,
    UnauthorizedDeviceError,
)
from telemetry.device.domain.ports import Clock
from telemetry.device.infrastructure.in_memory_registry import (
    InMemoryCredentialStore,
    InMemoryDeviceRegistry,
)


class _FixedNow(Clock):
    def __init__(self, instant: datetime) -> None:
        self._instant = instant

    def now(self) -> datetime:
        return self._instant


def _make_app() -> DeviceApplication:
    return DeviceApplication(
        DeviceManagement(
            registry=InMemoryDeviceRegistry(),
            credentials=InMemoryCredentialStore(),
            clock=_FixedNow(datetime(2026, 1, 1, tzinfo=timezone.utc)),
        )
    )


class DeviceApplicationTest(unittest.TestCase):
    def test_register_and_provision_happy_path(self) -> None:
        app = _make_app()
        reg = app.register_device(RegisterDeviceRequest(device_id="device-42"))
        self.assertTrue(reg.registered)
        prov = app.provision_credential(
            ProvisionCredentialRequest(
                device_id="device-42", credential_id="key-1"
            )
        )
        self.assertTrue(prov.provisioned)
        auth = app.authorize_device(
            AuthorizeDeviceRequest(
                device_id="device-42", credential_id="key-1"
            )
        )
        self.assertTrue(auth.authorized)
        self.assertEqual(auth.reason, "authorized")

    def test_unregistered_device_rejected(self) -> None:
        app = _make_app()
        auth = app.authorize_device(
            AuthorizeDeviceRequest(
                device_id="device-999", credential_id="key-1"
            )
        )
        self.assertFalse(auth.authorized)
        self.assertEqual(auth.reason, "device not registered or inactive")

    def test_provision_for_unregistered_device_rejected(self) -> None:
        app = _make_app()
        with self.assertRaises(UnauthorizedDeviceError):
            app.provision_credential(
                ProvisionCredentialRequest(
                    device_id="device-999", credential_id="key-1"
                )
            )

    def test_revoked_credential_rejected(self) -> None:
        app = _make_app()
        app.register_device(RegisterDeviceRequest(device_id="device-42"))
        app.provision_credential(
            ProvisionCredentialRequest(
                device_id="device-42", credential_id="key-1"
            )
        )
        app.revoke_credential(RevokeCredentialRequest(credential_id="key-1"))
        auth = app.authorize_device(
            AuthorizeDeviceRequest(
                device_id="device-42", credential_id="key-1"
            )
        )
        self.assertFalse(auth.authorized)

    def test_revoke_unknown_credential_rejected(self) -> None:
        app = _make_app()
        with self.assertRaises(InvalidCredentialError):
            app.revoke_credential(RevokeCredentialRequest(credential_id="key-9"))

    def test_rotation_invalidates_old_activates_new(self) -> None:
        app = _make_app()
        app.register_device(RegisterDeviceRequest(device_id="device-42"))
        app.provision_credential(
            ProvisionCredentialRequest(
                device_id="device-42", credential_id="key-1"
            )
        )
        app.rotate_credential(
            RotateCredentialRequest(
                device_id="device-42",
                old_credential_id="key-1",
                new_credential_id="key-2",
            )
        )
        old = app.authorize_device(
            AuthorizeDeviceRequest(
                device_id="device-42", credential_id="key-1"
            )
        )
        self.assertFalse(old.authorized)
        new = app.authorize_device(
            AuthorizeDeviceRequest(
                device_id="device-42", credential_id="key-2"
            )
        )
        self.assertTrue(new.authorized)

    def test_query_devices_active_count(self) -> None:
        app = _make_app()
        app.register_device(RegisterDeviceRequest(device_id="device-42"))
        app.register_device(RegisterDeviceRequest(device_id="device-99"))
        result = app.query_devices()
        self.assertEqual(result.active_count, 2)
        ids = {d.device_id for d in result.devices}
        self.assertEqual(ids, {"device-42", "device-99"})


class DomainModelReuseTest(unittest.TestCase):
    """Domain aggregates remain immutable through the application layer."""

    def test_device_immutable(self) -> None:
        device = Device(
            device_id="device-42",
            registered_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
        with self.assertRaises(Exception):
            device.device_id = "other"  # type: ignore[attr-defined]

    def test_credential_revoke_returns_new_instance(self) -> None:
        credential = Credential.create("key-1", "device-42")
        revoked = credential.revoke(datetime(2026, 2, 1, tzinfo=timezone.utc))
        self.assertIsNot(revoked, credential)
        self.assertTrue(credential.active)
        self.assertFalse(revoked.active)


if __name__ == "__main__":
    unittest.main()
