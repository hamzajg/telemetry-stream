"""EnvVarCredentialStore tests — pure Python, no framework.

Tests the production env-var credential store adapter. Reads
DEVICE_CREDENTIAL_<credential_id>=<device_id> from os.environ.

Scenario: credentials are loaded from environment variables
"""

from __future__ import annotations

import os
import unittest

from telemetry.device.domain.model import Credential
from telemetry.device.infrastructure.env_var_credential_store import (
    EnvVarCredentialStore,
)


class EnvVarCredentialStoreTest(unittest.TestCase):
    def setUp(self) -> None:
        self._store = EnvVarCredentialStore()
        self._env_keys: list[str] = []

    def _set_env(self, credential_id: str, device_id: str) -> None:
        key = f"DEVICE_CREDENTIAL_{credential_id}"
        os.environ[key] = device_id
        self._env_keys.append(key)

    def tearDown(self) -> None:
        for key in self._env_keys:
            os.environ.pop(key, None)
        self._env_keys = []

    def test_get_known_credential_returns_active(self) -> None:
        self._set_env("key-1", "device-42")
        credential = self._store.get("key-1")
        self.assertIsNotNone(credential)
        self.assertEqual(credential.credential_id, "key-1")
        self.assertEqual(credential.device_id, "device-42")
        self.assertTrue(credential.active)
        self.assertIsNone(credential.revoked_at)

    def test_get_unknown_credential_returns_none(self) -> None:
        self.assertIsNone(self._store.get("key-missing"))

    def test_get_empty_value_returns_none(self) -> None:
        os.environ["DEVICE_CREDENTIAL_empty"] = ""
        self._env_keys.append("DEVICE_CREDENTIAL_empty")
        self.assertIsNone(self._store.get("empty"))

    def test_save_raises_not_implemented(self) -> None:
        credential = Credential.create("key-9", "device-42")
        with self.assertRaises(NotImplementedError):
            self._store.save(credential)

    def test_get_case_sensitive_credential_id(self) -> None:
        self._set_env("Key-1", "device-42")
        self.assertIsNotNone(self._store.get("Key-1"))
        self.assertIsNone(self._store.get("key-1"))


if __name__ == "__main__":
    unittest.main()
