"""Device management application layer.

Orchestrates the domain service and adapters. Depends on ports
(interfaces), not on concrete implementations.
"""

from __future__ import annotations

from dataclasses import dataclass

from telemetry.device.domain.model import (
    AuthorizeDeviceCommand,
    Device,
    DeviceManagement,
    ProvisionCredentialCommand,
    QueryDevicesCommand,
    RegisterDeviceCommand,
    RevokeCredentialCommand,
    RotateCredentialCommand,
)


@dataclass(frozen=True)
class RegisterDeviceRequest:
    device_id: str


@dataclass(frozen=True)
class RegisterDeviceResponse:
    registered: bool
    device_id: str
    active: bool


@dataclass(frozen=True)
class ProvisionCredentialRequest:
    device_id: str
    credential_id: str


@dataclass(frozen=True)
class ProvisionCredentialResponse:
    provisioned: bool
    device_id: str
    credential_id: str


@dataclass(frozen=True)
class AuthorizeDeviceRequest:
    device_id: str
    credential_id: str


@dataclass(frozen=True)
class AuthorizeDeviceResponse:
    authorized: bool
    device_id: str
    credential_id: str
    reason: str


@dataclass(frozen=True)
class RevokeCredentialRequest:
    credential_id: str


@dataclass(frozen=True)
class RevokeCredentialResponse:
    revoked: bool
    credential_id: str


@dataclass(frozen=True)
class RotateCredentialRequest:
    device_id: str
    old_credential_id: str
    new_credential_id: str


@dataclass(frozen=True)
class RotateCredentialResponse:
    rotated: bool
    device_id: str
    old_credential_id: str
    new_credential_id: str


@dataclass(frozen=True)
class QueryDevicesResponse:
    active_count: int
    devices: list[Device]


class DeviceApplication:
    """Application layer: exposes device management use cases."""

    def __init__(self, device_management: DeviceManagement) -> None:
        self._dm = device_management

    def register_device(
        self, request: RegisterDeviceRequest
    ) -> RegisterDeviceResponse:
        result = self._dm.register(
            RegisterDeviceCommand(device_id=request.device_id)
        )
        return RegisterDeviceResponse(
            registered=result.registered,
            device_id=result.device_id,
            active=result.active,
        )

    def provision_credential(
        self, request: ProvisionCredentialRequest
    ) -> ProvisionCredentialResponse:
        result = self._dm.provision_credential(
            ProvisionCredentialCommand(
                device_id=request.device_id,
                credential_id=request.credential_id,
            )
        )
        return ProvisionCredentialResponse(
            provisioned=result.provisioned,
            device_id=result.device_id,
            credential_id=result.credential_id,
        )

    def authorize_device(
        self, request: AuthorizeDeviceRequest
    ) -> AuthorizeDeviceResponse:
        result = self._dm.authorize_device(
            AuthorizeDeviceCommand(
                device_id=request.device_id,
                credential_id=request.credential_id,
            )
        )
        return AuthorizeDeviceResponse(
            authorized=result.authorized,
            device_id=result.device_id,
            credential_id=result.credential_id,
            reason=result.reason,
        )

    def revoke_credential(
        self, request: RevokeCredentialRequest
    ) -> RevokeCredentialResponse:
        result = self._dm.revoke_credential(
            RevokeCredentialCommand(credential_id=request.credential_id)
        )
        return RevokeCredentialResponse(
            revoked=result.revoked,
            credential_id=result.credential_id,
        )

    def rotate_credential(
        self, request: RotateCredentialRequest
    ) -> RotateCredentialResponse:
        result = self._dm.rotate_credential(
            RotateCredentialCommand(
                device_id=request.device_id,
                old_credential_id=request.old_credential_id,
                new_credential_id=request.new_credential_id,
            )
        )
        return RotateCredentialResponse(
            rotated=result.rotated,
            device_id=result.device_id,
            old_credential_id=result.old_credential_id,
            new_credential_id=result.new_credential_id,
        )

    def query_devices(self) -> QueryDevicesResponse:
        result = self._dm.query_devices(QueryDevicesCommand())
        return QueryDevicesResponse(
            active_count=result.active_count,
            devices=result.devices,
        )


class CredentialApplication:
    """Application layer: exposes credential management use cases."""

    def __init__(self, device_management: DeviceManagement) -> None:
        self._dm = device_management

    def provision_credential(
        self, request: ProvisionCredentialRequest
    ) -> ProvisionCredentialResponse:
        result = self._dm.provision_credential(
            ProvisionCredentialCommand(
                device_id=request.device_id,
                credential_id=request.credential_id,
            )
        )
        return ProvisionCredentialResponse(
            provisioned=result.provisioned,
            device_id=result.device_id,
            credential_id=result.credential_id,
        )

    def revoke_credential(
        self, request: RevokeCredentialRequest
    ) -> RevokeCredentialResponse:
        result = self._dm.revoke_credential(
            RevokeCredentialCommand(credential_id=request.credential_id)
        )
        return RevokeCredentialResponse(
            revoked=result.revoked,
            credential_id=result.credential_id,
        )

    def rotate_credential(
        self, request: RotateCredentialRequest
    ) -> RotateCredentialResponse:
        result = self._dm.rotate_credential(
            RotateCredentialCommand(
                device_id=request.device_id,
                old_credential_id=request.old_credential_id,
                new_credential_id=request.new_credential_id,
            )
        )
        return RotateCredentialResponse(
            rotated=result.rotated,
            device_id=result.device_id,
            old_credential_id=result.old_credential_id,
            new_credential_id=result.new_credential_id,
        )
