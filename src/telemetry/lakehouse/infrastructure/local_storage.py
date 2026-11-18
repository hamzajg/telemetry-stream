"""Local filesystem test double for the LakehouseStorage port.

Pure Python, no S3. Writes JSONL files partitioned by device_id and event_date.
Used by domain/core tests so they run without object storage. Not used in
production.
"""

from __future__ import annotations

import json
import os
from typing import Dict, Set

from telemetry.lakehouse.domain.model import DuplicateOffsetError, LakehouseRow
from telemetry.lakehouse.domain.ports import LakehouseStorage


class LocalLakehouseStorage(LakehouseStorage):
    """Local filesystem lakehouse — JSONL files, partition-keyed by device_id/date."""

    def __init__(self, root_dir: str) -> None:
        self._root_dir = root_dir
        self._written: Set[str] = set()  # partition_path|row_key

    def _row_path(self, partition_path: str, row_key: str) -> str:
        return os.path.join(self._root_dir, partition_path, f"{row_key}.jsonl")

    def exists(self, partition_path: str, row_key: str) -> bool:
        return f"{partition_path}|{row_key}" in self._written or os.path.exists(
            self._row_path(partition_path, row_key)
        )

    def write(self, partition_path: str, row_key: str, row: LakehouseRow) -> None:
        key = f"{partition_path}|{row_key}"
        if key in self._written:
            raise DuplicateOffsetError(f"offset {row_key} already written")
        path = self._row_path(partition_path, row_key)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            f.write(
                json.dumps(
                    {
                        "device_id": row.device_id,
                        "sequence": row.sequence,
                        "offset": row.offset,
                        "event_date": row.event_date,
                        "payload": row.payload,
                        "written_at": row.written_at.isoformat(),
                    }
                )
            )
        self._written.add(key)
