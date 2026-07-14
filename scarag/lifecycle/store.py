from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable


def _utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


@dataclass
class LifecycleRecord:
    source_unit_id: str
    source: str
    content_fingerprint: str
    ingestion_iso_ts: str
    last_upsert_iso_ts: str
    deletion_mark_iso_ts: str | None
    status: str


class LifecycleStateStore:
    """Persist lifecycle metadata in a small file-backed state store."""

    def __init__(
        self,
        state_path: str | Path,
        now_provider: Callable[[], str] | None = None,
    ) -> None:
        self._state_path = Path(state_path)
        self._now_provider = now_provider or _utc_now_iso
        self._records: dict[str, LifecycleRecord] = self._load_state()

    def _load_state(self) -> dict[str, LifecycleRecord]:
        if not self._state_path.exists():
            return {}
        try:
            raw = json.loads(self._state_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}

        records: dict[str, LifecycleRecord] = {}
        for source_unit_id, value in raw.items():
            if not isinstance(value, dict):
                continue
            records[source_unit_id] = LifecycleRecord(
                source_unit_id=source_unit_id,
                source=str(value.get("source", "")),
                content_fingerprint=str(value.get("content_fingerprint", "")),
                ingestion_iso_ts=str(value.get("ingestion_iso_ts", "")),
                last_upsert_iso_ts=str(value.get("last_upsert_iso_ts", "")),
                deletion_mark_iso_ts=(
                    str(value.get("deletion_mark_iso_ts"))
                    if value.get("deletion_mark_iso_ts") is not None
                    else None
                ),
                status=str(value.get("status", "active")),
            )
        return records

    def _save_state(self) -> None:
        self._state_path.parent.mkdir(parents=True, exist_ok=True)
        serializable = {
            source_unit_id: asdict(record)
            for source_unit_id, record in sorted(self._records.items())
        }
        self._state_path.write_text(
            json.dumps(serializable, indent=2, sort_keys=True),
            encoding="utf-8",
        )

    def get(self, source_unit_id: str) -> LifecycleRecord | None:
        return self._records.get(source_unit_id)

    def upsert(
        self,
        *,
        source_unit_id: str,
        source: str,
        content_fingerprint: str,
    ) -> LifecycleRecord:
        now_iso = self._now_provider()
        existing = self._records.get(source_unit_id)

        if existing is None:
            record = LifecycleRecord(
                source_unit_id=source_unit_id,
                source=source,
                content_fingerprint=content_fingerprint,
                ingestion_iso_ts=now_iso,
                last_upsert_iso_ts=now_iso,
                deletion_mark_iso_ts=None,
                status="active",
            )
        else:
            record = LifecycleRecord(
                source_unit_id=source_unit_id,
                source=source,
                content_fingerprint=content_fingerprint,
                ingestion_iso_ts=existing.ingestion_iso_ts or now_iso,
                last_upsert_iso_ts=now_iso,
                deletion_mark_iso_ts=None,
                status="active",
            )

        self._records[source_unit_id] = record
        self._save_state()
        return record

    def soft_delete(self, source_unit_id: str) -> LifecycleRecord | None:
        record = self._records.get(source_unit_id)
        if record is None:
            return None

        now_iso = self._now_provider()
        updated = LifecycleRecord(
            source_unit_id=record.source_unit_id,
            source=record.source,
            content_fingerprint=record.content_fingerprint,
            ingestion_iso_ts=record.ingestion_iso_ts,
            last_upsert_iso_ts=record.last_upsert_iso_ts,
            deletion_mark_iso_ts=now_iso,
            status="soft_deleted",
        )
        self._records[source_unit_id] = updated
        self._save_state()
        return updated

    def set_status(self, source_unit_id: str, status: str) -> LifecycleRecord | None:
        record = self._records.get(source_unit_id)
        if record is None:
            return None

        updated = LifecycleRecord(
            source_unit_id=record.source_unit_id,
            source=record.source,
            content_fingerprint=record.content_fingerprint,
            ingestion_iso_ts=record.ingestion_iso_ts,
            last_upsert_iso_ts=self._now_provider(),
            deletion_mark_iso_ts=record.deletion_mark_iso_ts,
            status=status.strip() or record.status,
        )
        self._records[source_unit_id] = updated
        self._save_state()
        return updated

    def as_dict(self) -> dict[str, dict[str, Any]]:
        return {source_unit_id: asdict(record) for source_unit_id, record in self._records.items()}