"""Device management unit tests — pure Python, no Kafka, no framework.

Tests the domain core against in-memory doubles implementing the ports,
proving the domain is independently testable (hexagonal: policy depends on
nothing). Wave 1 scenarios:

- registered device is provisioned with credentials and can produce telemetry
"""

from __future__ import annotations

import unittest
from datetime import datetime, timezone

from telemetry.device.domain.model import (
    AuthorizeDeviceCommand,
    AuthorizeDeviceResult,
    Credential,
    Device,
    DeviceAlreadyRegisteredError,
    DeviceManagement,
    InvalidCredentialError,
    ProvisionCredentialCommand,
    ProvisionCredentialResult,
    QueryDevicesCommand,
    RegisterDeviceCommand,
    RevokeCredentialCommand,
    RevokeCredentialResult,
    RotateCredentialCommand,
    RotateCredentialResult,
    UnauthorizedDeviceError,
)
from telemetry.device.domain.ports import (
    Clock,
    CredentialStore,
    DeviceRegistry,
)
from telemetry.device.infrastructure.in_memory_registry import (
    InMemoryCredentialStore,
    InMemoryDeviceRegistry,
)


class _FixedNow(Clock):
    def __init__(self, instant: datetime) -> None:
        self._instant = instant

    def now(self) -> datetime:
        return self._instant


class DeviceTest(unittest.TestCase):
    def test_active_device(self) -> None:
        device = Device(
            device_id="device-42",
            registered_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
            active=True,
        )
        self.assertEqual(device.device_id, "device-42")
        self.assertTrue(device.active)

    def test_immutable(self) -> None:
        device = Device(
            device_id="device-42",
            registered_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
        with self.assertRaises(Exception):
            device.device_id = "other"  # type: ignore[attr-defined]


class CredentialTest(unittest.TestCase):
    def test_create_active(self) -> None:
        credential = Credential.create("key-1", "device-42")
        self.assertTrue(credential.active)
        self.assertIsNone(credential.revoked_at)
        self.assertIsNotNone(credential.created_at)

    def test_revoke_returns_new_instance(self) -> None:
        credential = Credential.create("key-1", "device-42")
        revoked = credential.revoke(datetime(2026, 2, 1, tzinfo=timezone.utc))
        self.assertIsNot(revoked, credential)
        self.assertFalse(revoked.active)
        self.assertEqual(revoked.revoked_at, datetime(2026, 2, 1, tzinfo=timezone.utc))
        # original unchanged
        self.assertTrue(credential.active)
        self.assertIsNone(credential.revoked_at)


class DeviceManagementTest(unittest.TestCase):
    def _make_service(self) -> DeviceManagement:
        return DeviceManagement(
            registry=InMemoryDeviceRegistry(),
            credentials=InMemoryCredentialStore(),
            clock=_FixedNow(datetime(2026, 1, 1, tzinfo=timezone.utc)),
        )

    def test_register_device(self) -> None:
        service = self._make_service()
        result = service.register(RegisterDeviceCommand(device_id="device-42"))
        self.assertTrue(result.registered)
        self.assertEqual(result.device_id, "device-42")
        self.assertTrue(result.active)

    def test_register_duplicate_rejected(self) -> None:
        service = self._make_service()
        service.register(RegisterDeviceCommand(device_id="device-42"))
        with self.assertRaises(DeviceAlreadyRegisteredError):
            service.register(RegisterDeviceCommand(device_id="device-42"))

    def test_provision_credential_for_registered_device(self) -> None:
        service = self._make_service()
        service.register(RegisterDeviceCommand(device_id="device-42"))
        result = service.provision_credential(
            ProvisionCredentialCommand(device_id="device-42", credential_id="key-1")
        )
        self.assertTrue(result.provisioned)
        self.assertEqual(result.device_id, "device-42")
        self.assertEqual(result.credential_id, "key-1")

    def test_provision_credential_for_unregistered_device_rejected(self) -> None:
        service = self._make_service()
        with self.assertRaises(UnauthorizedDeviceError):
            service.provision_credential(
                ProvisionCredentialCommand(
                    device_id="device-999", credential_id="key-1"
                )
            )

    def test_authorize_registered_active_device_with_active_credential(self) -> None:
        service = self._make_service()
        service.register(RegisterDeviceCommand(device_id="device-42"))
        service.provision_credential(
            ProvisionCredentialCommand(device_id="device-42", credential_id="key-1")
        )
        result = service.authorize_device(
            AuthorizeDeviceCommand(device_id="device-42", credential_id="key-1")
        )
        self.assertTrue(result.authorized)
        self.assertEqual(result.reason, "authorized")

    def test_authorize_unregistered_device_rejected(self) -> None:
        service = self._make_service()
        result = service.authorize_device(
            AuthorizeDeviceCommand(device_id="device-999", credential_id="key-1")
        )
        self.assertFalse(result.authorized)
        self.assertEqual(result.reason, "device not registered or inactive")

    def test_authorize_with_inactive_credential_rejected(self) -> None:
        service = self._make_service()
        service.register(RegisterDeviceCommand(device_id="device-42"))
        service.provision_credential(
            ProvisionCredentialCommand(device_id="device-42", credential_id="key-1")
        )
        service.revoke_credential(RevokeCredentialCommand(credential_id="key-1"))
        result = service.authorize_device(
            AuthorizeDeviceCommand(device_id="device-42", credential_id="key-1")
        )
        self.assertFalse(result.authorized)
        self.assertEqual(
            result.reason, "credential unknown, inactive, or revoked"
        )

    def test_authorize_with_wrong_device_credential_rejected(self) -> None:
        service = self._make_service()
        service.register(RegisterDeviceCommand(device_id="device-42"))
        service.register(RegisterDeviceCommand(device_id="device-43"))
        service.provision_credential(
            ProvisionCredentialCommand(device_id="device-42", credential_id="key-1")
        )
        result = service.authorize_device(
            AuthorizeDeviceCommand(device_id="device-43", credential_id="key-1")
        )
        self.assertFalse(result.authorized)
        self.assertEqual(result.reason, "credential does not belong to device")

    def test_revoke_credential(self) -> None:
        service = self._make_service()
        service.register(RegisterDeviceCommand(device_id="device-42"))
        service.provision_credential(
            ProvisionCredentialCommand(device_id="device-42", credential_id="key-1")
        )
        result = service.revoke_credential(
            RevokeCredentialCommand(credential_id="key-1")
        )
        self.assertTrue(result.revoked)
        self.assertEqual(result.credential_id, "key-1")

    def test_revoke_unknown_credential_rejected(self) -> None:
        service = self._make_service()
        with self.assertRaises(InvalidCredentialError):
            service.revoke_credential(RevokeCredentialCommand(credential_id="key-9"))

    def test_rotate_invalidates_old_activates_new(self) -> None:
        service = self._make_service()
        service.register(RegisterDeviceCommand(device_id="device-42"))
        service.provision_credential(
            ProvisionCredentialCommand(device_id="device-42", credential_id="key-1")
        )
        result = service.rotate_credential(
            RotateCredentialCommand(
                device_id="device-42",
                old_credential_id="key-1",
                new_credential_id="key-2",
            )
        )
        self.assertTrue(result.rotated)
        self.assertEqual(result.old_credential_id, "key-1")
        self.assertEqual(result.new_credential_id, "key-2")

        # old no longer authorizes
        old = service.authorize_device(
            AuthorizeDeviceCommand(device_id="device-42", credential_id="key-1")
        )
        self.assertFalse(old.authorized)
        # new authorizes
        new = service.authorize_device(
            AuthorizeDeviceCommand(device_id="device-42", credential_id="key-2")
        )
        self.assertTrue(new.authorized)

    def test_rotate_unknown_old_credential_rejected(self) -> None:
        service = self._make_service()
        with self.assertRaises(InvalidCredentialError):
            service.rotate_credential(
                RotateCredentialCommand(
                    device_id="device-42",
                    old_credential_id="key-1",
                    new_credential_id="key-2",
                )
            )

    def test_query_devices_active_count(self) -> None:
        service = self._make_service()
        service.register(RegisterDeviceCommand(device_id="device-42"))
        service.register(RegisterDeviceCommand(device_id="device-99"))
        result = service.query_devices(QueryDevicesCommand())
        self.assertEqual(result.active_count, 2)

    def test_query_devices_returns_details(self) -> None:
        service = self._make_service()
        service.register(RegisterDeviceCommand(device_id="device-42"))
        result = service.query_devices(QueryDevicesCommand())
        self.assertEqual(len(result.devices), 1)
        self.assertEqual(result.devices[0].device_id, "device-42")


class InMemoryRegistryTest(unittest.TestCase):
    def test_save_then_get(self) -> None:
        registry = InMemoryDeviceRegistry()
        device = Device(
            device_id="device-42",
            registered_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
        registry.save(device)
        self.assertEqual(registry.get("device-42"), device)
        self.assertIsNone(registry.get("device-99"))

    def test_list_active_only(self) -> None:
        registry = InMemoryDeviceRegistry()
        active = Device(
            device_id="device-42",
            registered_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
            active=True,
        )
        inactive = Device(
            device_id="device-43",
            registered_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
            active=False,
        )
        registry.save(active)
        registry.save(inactive)
        listed = registry.list_active()
        self.assertEqual(len(listed), 1)
        self.assertEqual(listed[0].device_id, "device-42")


class InMemoryCredentialStoreTest(unittest.TestCase):
    def test_save_then_get(self) -> None:
        store = InMemoryCredentialStore()
        credential = Credential.create("key-1", "device-42")
        store.save(credential)
        self.assertEqual(store.get("key-1"), credential)
        self.assertIsNone(store.get("key-2"))

    def test_save_upserts_existing(self) -> None:
        store = InMemoryCredentialStore()
        credential = Credential.create("key-1", "device-42")
        store.save(credential)
        revoked = credential.revoke(datetime(2026, 2, 1, tzinfo=timezone.utc))
        store.save(revoked)
        self.assertFalse(store.get("key-1").active)


if __name__ == "__main__":
    unittest.main()
