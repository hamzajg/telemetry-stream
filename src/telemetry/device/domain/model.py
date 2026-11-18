"""Device management domain core.

Pure Python: imports no framework, cloud SDK, or database.
Business rules for device registration, credential provisioning,
authorization, revocation, and rotation.
Adapters implement the ports defined in :mod:`ports`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Protocol, runtime_checkable


class InvalidCredentialError(ValueError):
    """Raised when a credential is invalid or revoked."""


class UnauthorizedDeviceError(ValueError):
    """Raised when a device is not authorized to produce telemetry."""


class DeviceAlreadyRegisteredError(ValueError):
    """Raised when registering a device that already exists."""


class CredentialAlreadyRotatedError(ValueError):
    """Reserved: credential store save is an upsert; kept for compatibility."""


@dataclass(frozen=True)
class Device:
    """A registered device — the entity boundary.

    Attributes:
        device_id: stable identifier of the device.
        registered_at: when the device was registered (UTC).
        active: whether the device is currently active.
    """

    device_id: str
    registered_at: datetime
    active: bool = True


@dataclass(frozen=True)
class Credential:
    """A device credential — an immutable secret.

    Attributes:
        credential_id: stable identifier of the credential (e.g. API key).
        device_id: device this credential belongs to.
        active: whether the credential is currently valid.
        created_at: when the credential was created (UTC).
        revoked_at: when the credential was revoked, if ever.
    """

    credential_id: str
    device_id: str
    active: bool = True
    created_at: datetime | None = None
    revoked_at: datetime | None = None

    @classmethod
    def create(cls, credential_id: str, device_id: str) -> "Credential":
        return cls(
            credential_id=credential_id,
            device_id=device_id,
            active=True,
            created_at=datetime.now(timezone.utc),
            revoked_at=None,
        )

    def revoke(self, revoked_at: datetime) -> "Credential":
        """Return a new Credential revoked at ``revoked_at`` (immutable)."""
        return Credential(
            credential_id=self.credential_id,
            device_id=self.device_id,
            active=False,
            created_at=self.created_at,
            revoked_at=revoked_at,
        )


@dataclass(frozen=True)
class AuthorizedDevice:
    """Result of an authorization check.

    Attributes:
        device_id: device that was checked.
        authorized: whether the device may produce telemetry.
        reason: why the decision was made.
    """

    device_id: str
    authorized: bool
    reason: str


@dataclass(frozen=True)
class RegisterDeviceCommand:
    """Input to the register use case."""

    device_id: str


@dataclass(frozen=True)
class RegisterDeviceResult:
    """Outcome of registering a device."""

    registered: bool
    device_id: str
    active: bool


@dataclass(frozen=True)
class ProvisionCredentialCommand:
    """Input to the provision credential use case."""

    device_id: str
    credential_id: str


@dataclass(frozen=True)
class ProvisionCredentialResult:
    """Outcome of provisioning a credential."""

    provisioned: bool
    device_id: str
    credential_id: str


@dataclass(frozen=True)
class RevokeCredentialCommand:
    """Input to the revoke credential use case."""

    credential_id: str


@dataclass(frozen=True)
class RevokeCredentialResult:
    """Outcome of revoking a credential."""

    revoked: bool
    credential_id: str


@dataclass(frozen=True)
class RotateCredentialCommand:
    """Input to the rotate credential use case."""

    device_id: str
    old_credential_id: str
    new_credential_id: str


@dataclass(frozen=True)
class RotateCredentialResult:
    """Outcome of rotating a credential."""

    rotated: bool
    device_id: str
    old_credential_id: str
    new_credential_id: str


@dataclass(frozen=True)
class AuthorizeDeviceCommand:
    """Input to the authorize use case."""

    device_id: str
    credential_id: str


@dataclass(frozen=True)
class AuthorizeDeviceResult:
    """Outcome of authorizing a device."""

    authorized: bool
    device_id: str
    credential_id: str
    reason: str


@dataclass(frozen=True)
class QueryDevicesCommand:
    """Input to the query use case."""


@dataclass(frozen=True)
class QueryDevicesResult:
    """Outcome of querying devices."""

    active_count: int
    devices: list[Device]


@runtime_checkable
class DeviceRegistry(Protocol):
    """Port: device registry store (e.g. in-memory dict, database)."""

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
    """Port: credential store (e.g. env vars, secret manager)."""

    def get(self, credential_id: str) -> Credential | None:
        """Return the credential for ``credential_id``, or None if unknown."""

    def save(self, credential: Credential) -> None:
        """Persist ``credential``.

        Raises CredentialAlreadyRotatedError if the credential already exists.
        """


@runtime_checkable
class Clock(Protocol):
    """Port: injectable time seam for deterministic tests."""

    def now(self) -> datetime:
        """Return the current UTC time."""


class DeviceManagement:
    """Domain service: register, provision, authorize, revoke, rotate.

    Stateless: holds no device state. The registry and credential store
    hold state; the service orchestrates business rules.
    """

    def __init__(
        self,
        registry: DeviceRegistry,
        credentials: CredentialStore,
        clock: Clock,
    ) -> None:
        self._registry = registry
        self._credentials = credentials
        self._clock = clock

    def register(self, command: RegisterDeviceCommand) -> RegisterDeviceResult:
        """Register one device.

        1. Build the immutable Device aggregate.
        2. Save to registry (rejects duplicates).
        """
        device = Device(
            device_id=command.device_id,
            registered_at=self._clock.now(),
            active=True,
        )
        self._registry.save(device)
        return RegisterDeviceResult(
            registered=True,
            device_id=command.device_id,
            active=True,
        )

    def provision_credential(
        self, command: ProvisionCredentialCommand
    ) -> ProvisionCredentialResult:
        """Provision one credential for a device.

        1. Verify the device is registered.
        2. Build the immutable Credential aggregate.
        3. Save to credential store (rejects duplicates).
        """
        device = self._registry.get(command.device_id)
        if device is None or not device.active:
            raise UnauthorizedDeviceError(
                f"device {command.device_id} is not registered"
            )

        credential = Credential.create(
            credential_id=command.credential_id,
            device_id=command.device_id,
        )
        self._credentials.save(credential)

        return ProvisionCredentialResult(
            provisioned=True,
            device_id=command.device_id,
            credential_id=command.credential_id,
        )

    def revoke_credential(
        self, command: RevokeCredentialCommand
    ) -> RevokeCredentialResult:
        """Revoke one credential.

        1. Load the credential.
        2. Revoke it (immutable new instance).
        3. Save back to the store.
        """
        credential = self._credentials.get(command.credential_id)
        if credential is None:
            raise InvalidCredentialError(
                f"credential {command.credential_id} is unknown"
            )

        revoked = credential.revoke(self._clock.now())
        self._credentials.save(revoked)

        return RevokeCredentialResult(
            revoked=True,
            credential_id=command.credential_id,
        )

    def rotate_credential(
        self, command: RotateCredentialCommand
    ) -> RotateCredentialResult:
        """Rotate one credential.

        1. Verify the old credential belongs to the device and is active.
        2. Revoke the old credential.
        3. Provision the new credential.
        """
        old_credential = self._credentials.get(command.old_credential_id)
        if old_credential is None:
            raise InvalidCredentialError(
                f"credential {command.old_credential_id} is unknown"
            )
        if old_credential.device_id != command.device_id:
            raise UnauthorizedDeviceError(
                f"credential {command.old_credential_id} does not belong to "
                f"device {command.device_id}"
            )
        if not old_credential.active:
            raise InvalidCredentialError(
                f"credential {command.old_credential_id} is not active"
            )

        self.revoke_credential(
            RevokeCredentialCommand(credential_id=command.old_credential_id)
        )

        new_credential = Credential.create(
            credential_id=command.new_credential_id,
            device_id=command.device_id,
        )
        self._credentials.save(new_credential)

        return RotateCredentialResult(
            rotated=True,
            device_id=command.device_id,
            old_credential_id=command.old_credential_id,
            new_credential_id=command.new_credential_id,
        )

    def authorize_device(
        self, command: AuthorizeDeviceCommand
    ) -> AuthorizeDeviceResult:
        """Authorize one device/credential pair to produce telemetry.

        Allowlist: only registered, active devices with active credentials
        may produce. Everything else is rejected by default.
        """
        device = self._registry.get(command.device_id)
        if device is None or not device.active:
            return AuthorizeDeviceResult(
                authorized=False,
                device_id=command.device_id,
                credential_id=command.credential_id,
                reason="device not registered or inactive",
            )

        credential = self._credentials.get(command.credential_id)
        if credential is None or not credential.active:
            return AuthorizeDeviceResult(
                authorized=False,
                device_id=command.device_id,
                credential_id=command.credential_id,
                reason="credential unknown, inactive, or revoked",
            )
        if credential.device_id != command.device_id:
            return AuthorizeDeviceResult(
                authorized=False,
                device_id=command.device_id,
                credential_id=command.credential_id,
                reason="credential does not belong to device",
            )

        return AuthorizeDeviceResult(
            authorized=True,
            device_id=command.device_id,
            credential_id=command.credential_id,
            reason="authorized",
        )

    def query_devices(self, _command: QueryDevicesCommand) -> QueryDevicesResult:
        """Query all active devices in the registry."""
        devices = self._registry.list_active()
        return QueryDevicesResult(
            active_count=len(devices),
            devices=devices,
        )
