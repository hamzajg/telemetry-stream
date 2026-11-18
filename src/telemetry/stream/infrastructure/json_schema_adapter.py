"""JSON schema adapter implementing the TelemetrySchema port.

Reuses the same minimal validator as the ingestion feature so both domains
share a dependency-free validation contract. Swappable for Avro/JSON Schema
behind the same port.
"""

from __future__ import annotations

from telemetry.stream.domain.model import InvalidSchemaError


class JsonSchemaAdapter:
    """Validates telemetry payloads against a minimal schema.

    Required fields: ``reading_type`` (str), ``value`` (number).
    """

    def __init__(self, required_fields: tuple[str, ...] = ("reading_type", "value")) -> None:
        self._required_fields = required_fields

    def validate(self, payload: dict) -> None:
        if not isinstance(payload, dict):
            raise InvalidSchemaError("payload must be a JSON object")
        for field in self._required_fields:
            if field not in payload:
                raise InvalidSchemaError(f"missing required field: {field}")
            if payload[field] is None:
                raise InvalidSchemaError(f"field {field} must not be null")
        if "value" in payload and not isinstance(payload["value"], (int, float)):
            raise InvalidSchemaError("field value must be a number")
        if "reading_type" in payload and not isinstance(payload["reading_type"], str):
            raise InvalidSchemaError("field reading_type must be a string")
