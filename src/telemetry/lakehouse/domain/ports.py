"""Ports: interfaces the lakehouse domain depends on. Adapters implement these."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol, runtime_checkable

from telemetry.lakehouse.domain.model import LakehouseRow


@runtime_checkable
class LakehouseStorage(Protocol):
    """Durable, queryable object store (e.g. S3 + Parquet)."""

    def write(self, partition_path: str, row_key: str, row: LakehouseRow) -> None:
        """Write ``row`` to ``partition_path`` under ``row_key``.

        Raises DuplicateOffsetError if ``row_key`` already exists (idempotency).
        """

    def exists(self, partition_path: str, row_key: str) -> bool:
        """Return True if a row with ``row_key`` already exists at ``partition_path``."""


@runtime_checkable
class LakehouseCatalog(Protocol):
    """Table registration / catalog (e.g. Glue crawler)."""

    def register_table(self, table_name: str, partition_path: str) -> None:
        """Register a table for analytics queries."""

    def table_exists(self, table_name: str) -> bool:
        """Return True if ``table_name`` is registered."""


@runtime_checkable
class Clock(Protocol):
    """Injectable time seam for deterministic tests."""

    def now(self) -> datetime:
        """Return the current UTC time."""
