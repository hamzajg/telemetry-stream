"""Production infrastructure adapters for device management.

EnvVarCredentialStore reads credentials from environment variables
(DEVICE_CREDENTIAL_<credential_id>=<device_id>), satisfying the SPEC
decision D2 (environment variables / placeholders for credential storage,
swappable for a secret manager later). Read-only at runtime — provisioning
happens out-of-band by setting env vars before deploy.

``save`` persists credentials to an in-memory overlay so credentials can be
provisioned at runtime without redeploy. ``get`` checks env vars first, then
the in-memory overlay.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Dict

from telemetry.device.domain.model import Credential
from telemetry.device.domain.ports import CredentialStore


_CREDENTIAL_ENV_PREFIX = "DEVICE_CREDENTIAL_"


class EnvVarCredentialStore(CredentialStore):
    """Credential store backed by environment variables with an in-memory overlay.

    Reads ``DEVICE_CREDENTIAL_<credential_id>=<device_id>`` at lookup time.
    All credentials sourced from env vars are active. Revocation is not
    supported through this store (rotate by unsetting/changing the env var
    and redeploy).

    ``save`` persists to an in-memory overlay keyed by credential_id, so
    credentials can be provisioned at runtime. ``get`` checks env vars first,
    then falls back to the overlay.
    """

    def __init__(self) -> None:
        self._overlay: Dict[str, Credential] = {}

    def get(self, credential_id: str) -> Credential | None:
        device_id = os.environ.get(_CREDENTIAL_ENV_PREFIX + credential_id)
        if device_id is None or device_id == "":
            return self._overlay.get(credential_id)
        return Credential(
            credential_id=credential_id,
            device_id=device_id,
            active=True,
            created_at=None,
            revoked_at=None,
        )

    def save(self, credential: Credential) -> None:
        self._overlay[credential.credential_id] = credential
