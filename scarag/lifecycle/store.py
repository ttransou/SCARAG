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
        audit_log_path: str | Path | None = None,
        audit_logging_enabled: bool = False,
    ) -> None:
        self._state_path = Path(state_path)
        self._now_provider = now_provider or _utc_now_iso
        self._audit_log_path = Path(audit_log_path) if audit_log_path else None
        self._audit_logging_enabled = bool(audit_logging_enabled)
        self._records: dict[str, LifecycleRecord] = self._load_state()

    def _parse_iso(self, value: str | None) -> datetime | None:
        if not value:
            return None
        try:
            normalized = str(value).replace("Z", "+00:00")
            parsed = datetime.fromisoformat(normalized)
        except ValueError:
            return None
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=UTC)
        return parsed

    def _append_audit_event(self, action: str, source_unit_id: str, details: dict[str, Any] | None = None) -> None:
        if not self._audit_logging_enabled or self._audit_log_path is None:
            return
        payload: dict[str, Any] = {
            "event_iso_ts": self._now_provider(),
            "action": action,
            "source_unit_id": source_unit_id,
        }
        if details:
            payload["details"] = details

        self._audit_log_path.parent.mkdir(parents=True, exist_ok=True)
        with self._audit_log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, sort_keys=True) + "\n")

    def _iter_audit_events(self, audit_log_path: str | Path | None = None) -> list[dict[str, Any]]:
        path = Path(audit_log_path) if audit_log_path else self._audit_log_path
        if path is None or not path.exists():
            return []

        events: list[dict[str, Any]] = []
        try:
            content = path.read_text(encoding="utf-8")
        except OSError:
            return []

        for raw_line in content.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            try:
                parsed = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(parsed, dict):
                events.append(parsed)
        return events

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

    def upsert_with_policy(
        self,
        *,
        source_unit_id: str,
        source: str,
        content_fingerprint: str,
        skip_unchanged: bool = False,
    ) -> tuple[LifecycleRecord, str]:
        existing = self._records.get(source_unit_id)
        if (
            existing is not None
            and skip_unchanged
            and existing.content_fingerprint == content_fingerprint
        ):
            self._append_audit_event(
                "unchanged_skipped",
                source_unit_id,
                {
                    "source": source,
                    "status": existing.status,
                    "ingestion_iso_ts": existing.ingestion_iso_ts,
                    "last_upsert_iso_ts": existing.last_upsert_iso_ts,
                },
            )
            return existing, "unchanged_skipped"

        now_iso = self._now_provider()
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
            action = "created"
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
            action = "updated"

        self._records[source_unit_id] = record
        self._save_state()
        self._append_audit_event(
            action,
            source_unit_id,
            {
                "source": source,
                "status": record.status,
                "ingestion_iso_ts": record.ingestion_iso_ts,
                "last_upsert_iso_ts": record.last_upsert_iso_ts,
            },
        )
        return record, action

    def upsert(
        self,
        *,
        source_unit_id: str,
        source: str,
        content_fingerprint: str,
    ) -> LifecycleRecord:
        record, _action = self.upsert_with_policy(
            source_unit_id=source_unit_id,
            source=source,
            content_fingerprint=content_fingerprint,
            skip_unchanged=False,
        )
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
        self._append_audit_event(
            "soft_deleted",
            source_unit_id,
            {
                "source": updated.source,
                "status": updated.status,
                "deletion_mark_iso_ts": updated.deletion_mark_iso_ts,
            },
        )
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
        self._append_audit_event(
            "status_updated",
            source_unit_id,
            {
                "source": updated.source,
                "status": updated.status,
                "deletion_mark_iso_ts": updated.deletion_mark_iso_ts,
            },
        )
        return updated

    def build_audit_report(self, audit_log_path: str | Path | None = None) -> dict[str, Any]:
        status_counts: dict[str, int] = {}
        active_count = 0
        soft_deleted_count = 0
        missing_ingestion = 0
        missing_upsert = 0
        invalid_ingestion = 0
        invalid_upsert = 0

        for record in self._records.values():
            status = (record.status or "unknown").strip().lower() or "unknown"
            status_counts[status] = status_counts.get(status, 0) + 1
            if status == "active":
                active_count += 1
            if status == "soft_deleted" or bool(record.deletion_mark_iso_ts):
                soft_deleted_count += 1

            if not str(record.ingestion_iso_ts or "").strip():
                missing_ingestion += 1
            elif self._parse_iso(record.ingestion_iso_ts) is None:
                invalid_ingestion += 1

            if not str(record.last_upsert_iso_ts or "").strip():
                missing_upsert += 1
            elif self._parse_iso(record.last_upsert_iso_ts) is None:
                invalid_upsert += 1

        events = self._iter_audit_events(audit_log_path)
        event_counts: dict[str, int] = {}
        for event in events:
            action = str(event.get("action", "unknown")).strip().lower() or "unknown"
            event_counts[action] = event_counts.get(action, 0) + 1

        return {
            "state": {
                "total_records": len(self._records),
                "active_count": active_count,
                "soft_deleted_count": soft_deleted_count,
                "status_counts": dict(sorted(status_counts.items())),
            },
            "timestamps": {
                "missing_ingestion_iso_ts": missing_ingestion,
                "invalid_ingestion_iso_ts": invalid_ingestion,
                "missing_last_upsert_iso_ts": missing_upsert,
                "invalid_last_upsert_iso_ts": invalid_upsert,
            },
            "events": {
                "total_events": len(events),
                "event_counts": dict(sorted(event_counts.items())),
                "reingestion": {
                    "created": event_counts.get("created", 0),
                    "updated": event_counts.get("updated", 0),
                    "unchanged_skipped": event_counts.get("unchanged_skipped", 0),
                },
            },
        }

    def hard_purge_soft_deleted(
        self,
        *,
        older_than_days: int | None = None,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        now = self._parse_iso(self._now_provider()) or datetime.now(UTC)
        threshold_days = max(0, int(older_than_days)) if older_than_days is not None else None
        purged_ids: list[str] = []
        skipped_missing_deletion_ts = 0
        skipped_invalid_deletion_ts = 0

        for source_unit_id, record in sorted(self._records.items()):
            soft_deleted = record.status.strip().lower() == "soft_deleted" or bool(record.deletion_mark_iso_ts)
            if not soft_deleted:
                continue

            if threshold_days is not None:
                deletion_ts_raw = str(record.deletion_mark_iso_ts or "").strip()
                if not deletion_ts_raw:
                    skipped_missing_deletion_ts += 1
                    continue
                parsed_deletion_ts = self._parse_iso(deletion_ts_raw)
                if parsed_deletion_ts is None:
                    skipped_invalid_deletion_ts += 1
                    continue
                if (now - parsed_deletion_ts).days < threshold_days:
                    continue

            purged_ids.append(source_unit_id)

        if not dry_run and purged_ids:
            for source_unit_id in purged_ids:
                removed = self._records.pop(source_unit_id, None)
                if removed is None:
                    continue
                self._append_audit_event(
                    "hard_purged",
                    source_unit_id,
                    {
                        "source": removed.source,
                        "status": removed.status,
                        "deletion_mark_iso_ts": removed.deletion_mark_iso_ts,
                    },
                )
            self._save_state()

        return {
            "inspected_records": len(self._records),
            "purged_count": len(purged_ids),
            "purged_source_unit_ids": purged_ids,
            "skipped_missing_deletion_mark_iso_ts": skipped_missing_deletion_ts,
            "skipped_invalid_deletion_mark_iso_ts": skipped_invalid_deletion_ts,
            "dry_run": dry_run,
            "remaining_records": len(self._records) if not dry_run else len(self._records),
        }

    def as_dict(self) -> dict[str, dict[str, Any]]:
        return {source_unit_id: asdict(record) for source_unit_id, record in self._records.items()}