from __future__ import annotations

import json
from pathlib import Path

from scarag.config import RagConfig
from scarag.lifecycle import LifecycleStateStore
from scarag.pipeline import build_chunk_index


def test_chunk_index_includes_lifecycle_fields_and_persists_state(tmp_path: Path) -> None:
    state_path = tmp_path / "lifecycle-state.json"
    config = RagConfig(lifecycle_state_path=str(state_path))

    documents = [
        {
            "source": str(tmp_path / "policy.txt"),
            "text": "policy controls require periodic review and documented approvals",
            "doc_type": "policy",
        }
    ]

    chunks = build_chunk_index(documents, config)
    assert chunks

    first = chunks[0]
    assert first["source_unit_id"].startswith("su_")
    assert first["status"] == "active"
    assert first["deletion_mark_iso_ts"] is None
    assert first["ingestion_iso_ts"]
    assert first["last_upsert_iso_ts"]
    assert first["extraction_method"]
    assert first["extraction_ts"]
    assert isinstance(first["confidence_inputs"], dict)

    persisted = json.loads(state_path.read_text(encoding="utf-8"))
    assert first["source_unit_id"] in persisted
    assert persisted[first["source_unit_id"]]["status"] == "active"


def test_reingestion_preserves_ingestion_timestamp_and_updates_last_upsert(tmp_path: Path) -> None:
    timestamps = iter(["2026-01-01T00:00:00Z", "2026-01-02T00:00:00Z"])
    state_path = tmp_path / "lifecycle-state.json"
    store = LifecycleStateStore(state_path, now_provider=lambda: next(timestamps))
    config = RagConfig(lifecycle_state_path=str(state_path))

    source = str(tmp_path / "dataset.csv")
    first = build_chunk_index(
        [
            {
                "source": source,
                "text": "name,value\nalpha,1",
                "doc_type": "report",
            }
        ],
        config,
        lifecycle_store=store,
    )[0]
    second = build_chunk_index(
        [
            {
                "source": source,
                "text": "name,value\nalpha,2",
                "doc_type": "report",
            }
        ],
        config,
        lifecycle_store=store,
    )[0]

    assert first["source_unit_id"] == second["source_unit_id"]
    assert first["ingestion_iso_ts"] == "2026-01-01T00:00:00Z"
    assert second["ingestion_iso_ts"] == "2026-01-01T00:00:00Z"
    assert second["last_upsert_iso_ts"] == "2026-01-02T00:00:00Z"


def test_skip_unchanged_reingestion_is_flag_controlled_and_audited(tmp_path: Path) -> None:
    tick = {"value": 0}

    def _now() -> str:
        tick["value"] += 1
        return f"2026-02-{tick['value']:02d}T00:00:00Z"

    state_path = tmp_path / "lifecycle-state.json"
    audit_path = tmp_path / "lifecycle-audit.jsonl"
    store = LifecycleStateStore(
        state_path,
        now_provider=_now,
        audit_log_path=audit_path,
        audit_logging_enabled=True,
    )
    config = RagConfig(
        lifecycle_state_path=str(state_path),
        lifecycle_skip_unchanged=True,
        lifecycle_audit_logging_enabled=True,
        lifecycle_audit_log_path=str(audit_path),
    )

    source = str(tmp_path / "dataset.csv")
    first_chunks = build_chunk_index(
        [
            {
                "source": source,
                "text": "name,value\nalpha,1",
                "doc_type": "report",
            }
        ],
        config,
        lifecycle_store=store,
    )
    second_chunks = build_chunk_index(
        [
            {
                "source": source,
                "text": "name,value\nalpha,1",
                "doc_type": "report",
            }
        ],
        config,
        lifecycle_store=store,
    )
    third_chunks = build_chunk_index(
        [
            {
                "source": source,
                "text": "name,value\nalpha,2",
                "doc_type": "report",
            }
        ],
        config,
        lifecycle_store=store,
    )

    assert first_chunks
    assert not second_chunks
    assert third_chunks

    report = store.build_audit_report()
    assert report["events"]["reingestion"]["created"] == 1
    assert report["events"]["reingestion"]["unchanged_skipped"] == 1
    assert report["events"]["reingestion"]["updated"] == 1


def test_hard_purge_soft_deleted_supports_dry_run_and_audit_event(tmp_path: Path) -> None:
    tick = {"value": 0}

    def _now() -> str:
        tick["value"] += 1
        return f"2026-03-{tick['value']:02d}T00:00:00Z"

    state_path = tmp_path / "lifecycle-state.json"
    audit_path = tmp_path / "lifecycle-audit.jsonl"
    store = LifecycleStateStore(
        state_path,
        now_provider=_now,
        audit_log_path=audit_path,
        audit_logging_enabled=True,
    )

    store.upsert(source_unit_id="su_a", source="a.txt", content_fingerprint="fp_a")
    store.upsert(source_unit_id="su_b", source="b.txt", content_fingerprint="fp_b")
    deleted = store.soft_delete("su_a")
    assert deleted is not None

    preview = store.hard_purge_soft_deleted(dry_run=True)
    assert preview["purged_count"] == 1
    assert store.get("su_a") is not None

    result = store.hard_purge_soft_deleted()
    assert result["purged_count"] == 1
    assert store.get("su_a") is None
    assert store.get("su_b") is not None

    report = store.build_audit_report()
    assert report["events"]["event_counts"].get("hard_purged", 0) == 1