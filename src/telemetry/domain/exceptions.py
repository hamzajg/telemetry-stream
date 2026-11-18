"""Typed domain errors."""

from __future__ import annotations


class InvalidSchemaError(ValueError):
    """Raised when a telemetry event fails schema validation."""


class DuplicateOffsetError(ValueError):
    """Raised when an event would reuse an already-consumed offset."""


class IngestionError(RuntimeError):
    """Raised when ingestion fails for a reason outside schema validation."""
