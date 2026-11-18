"""Production infrastructure adapters for device management.

EnvVarCredentialStore reads credentials from environment variables
(DEVICE_CREDENTIAL_<credential_id>=<device_id>), satisfying the SPEC
decision D2 (environment variables / placeholders for credential storage,
swappable for a secret manager later). Read-only at runtime — provisioning
happens out-of-band by setting env vars before deploy.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone

from telemetry.device.domain.model import Credential
from telemetry.device.domain.ports import CredentialStore


_CREDENTIAL_ENV_PREFIX = "DEVICE_CREDENTIAL_"


class EnvVarCredentialStore(CredentialStore):
    """Credential store backed by environment variables.

    Reads ``DEVICE_CREDENTIAL_<credential_id>=<device_id>`` at lookup time.
    All credentials sourced from env vars are active. Revocation is not
    supported through this store (rotate by unsetting/changing the env var
    and redeploying).

    ``save`` is not supported — env vars are read-only configuration,
    provisioning happens out-of-band before deploy.
    """

    def get(self, credential_id: str) -> Credential | None:
        device_id = os.environ.get(_CREDENTIAL_ENV_PREFIX + credential_id)
        if device_id is None or device_id == "":
            return None
        return Credential(
            credential_id=credential_id,
            device_id=device_id,
            active=True,
            created_at=None,
            revoked_at=None,
        )

    def save(self, credential: Credential) -> None:
        raise NotImplementedError(
            "env-var credential store is read-only; provision credentials "
            "by setting DEVICE_CREDENTIAL_<id> before deploy"
        )
