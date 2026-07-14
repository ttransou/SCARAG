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