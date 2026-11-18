"""Local catalog test double for the LakehouseCatalog port.

Pure Python, no Glue. Tracks registered table names in memory.
Used by domain/core tests so they run without Glue/Athena. Not used in
production.
"""

from __future__ import annotations

from typing import Set

from telemetry.lakehouse.domain.ports import LakehouseCatalog


class LocalLakehouseCatalog(LakehouseCatalog):
    """In-memory catalog — tracks registered table names."""

    def __init__(self) -> None:
        self._tables: Set[str] = set()

    def register_table(self, table_name: str, partition_path: str) -> None:
        self._tables.add(table_name)

    def table_exists(self, table_name: str) -> bool:
        return table_name in self._tables
