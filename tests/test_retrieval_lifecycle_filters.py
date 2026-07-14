from __future__ import annotations

from pathlib import Path

from scarag.config import RagConfig
from scarag.lifecycle import LifecycleStateStore
from scarag.pipeline import build_chunk_index, retrieve_chunks, retrieve_chunks_with_diagnostics


def _build_docs(tmp_path: Path) -> list[dict[str, str]]:
    return [
        {
            "source": str(tmp_path / "policy.md"),
            "text": "policy review cadence and control ownership",
            "doc_type": "policy",
        },
        {
            "source": str(tmp_path / "guide.md"),
            "text": "guideline for onboarding and workflow",
            "doc_type": "guideline",
        },
    ]


def test_retrieve_excludes_soft_deleted_units(tmp_path: Path) -> None:
    state_path = tmp_path / "lifecycle-state.json"
    config = RagConfig(lifecycle_state_path=str(state_path), exclude_soft_deleted=True)
    docs = _build_docs(tmp_path)
    chunks = build_chunk_index(docs, config)

    policy_chunk = next(chunk for chunk in chunks if chunk["source"].endswith("policy.md"))
    store = LifecycleStateStore(state_path)
    store.soft_delete(policy_chunk["source_unit_id"])

    results = retrieve_chunks("policy", chunks, config, {"terms": {}, "intent_groups": {}})
    assert all(not str(item["source"]).endswith("policy.md") for item in results)


def test_retrieve_applies_status_allow_and_deny_filters(tmp_path: Path) -> None:
    state_path = tmp_path / "lifecycle-state.json"
    config = RagConfig(lifecycle_state_path=str(state_path))
    chunks = build_chunk_index(_build_docs(tmp_path), config)

    policy_chunk = next(chunk for chunk in chunks if chunk["source"].endswith("policy.md"))
    store = LifecycleStateStore(state_path)
    updated = store.set_status(policy_chunk["source_unit_id"], "pending_review")
    assert updated is not None

    config_allow = RagConfig(
        lifecycle_state_path=str(state_path),
        status_allow_list=["active"],
    )
    allow_results = retrieve_chunks("policy", chunks, config_allow, {"terms": {}, "intent_groups": {}})
    assert all(not str(item["source"]).endswith("policy.md") for item in allow_results)

    config_deny = RagConfig(
        lifecycle_state_path=str(state_path),
        status_deny_list=["pending_review"],
    )
    deny_results = retrieve_chunks("policy", chunks, config_deny, {"terms": {}, "intent_groups": {}})
    assert all(not str(item["source"]).endswith("policy.md") for item in deny_results)


def test_retrieve_applies_freshness_cutoff(tmp_path: Path) -> None:
    state_path = tmp_path / "lifecycle-state.json"
    store = LifecycleStateStore(state_path, now_provider=lambda: "2020-01-01T00:00:00Z")
    config = RagConfig(lifecycle_state_path=str(state_path))
    chunks = build_chunk_index(_build_docs(tmp_path), config, lifecycle_store=store)

    stale_config = RagConfig(
        lifecycle_state_path=str(state_path),
        freshness_max_age_days=30,
    )
    results = retrieve_chunks("policy", chunks, stale_config, {"terms": {}, "intent_groups": {}})
    assert not results


def test_retrieve_returns_lifecycle_filter_diagnostics(tmp_path: Path) -> None:
    state_path = tmp_path / "lifecycle-state.json"
    config = RagConfig(lifecycle_state_path=str(state_path), exclude_soft_deleted=True)
    chunks = build_chunk_index(_build_docs(tmp_path), config)

    policy_chunk = next(chunk for chunk in chunks if chunk["source"].endswith("policy.md"))
    store = LifecycleStateStore(state_path)
    store.soft_delete(policy_chunk["source_unit_id"])

    _, diagnostics = retrieve_chunks_with_diagnostics(
        "policy",
        chunks,
        config,
        {"terms": {}, "intent_groups": {}},
    )
    assert diagnostics["candidates"] >= 1
    assert diagnostics["filtered_soft_deleted"] >= 1


def test_freshness_missing_timestamp_policy_exclude_filters_chunk(tmp_path: Path) -> None:
    state_path = tmp_path / "lifecycle-state.json"
    chunks = [
        {
            "chunk_id": "orphan:0",
            "source_unit_id": "su_missing_record",
            "source": str(tmp_path / "orphan.txt"),
            "text": "policy note",
            "doc_type": "policy",
            "domain_area": "unknown",
            "is_tabular": False,
            "content_fingerprint": "abc",
            "ingestion_iso_ts": "",
            "last_upsert_iso_ts": "",
            "deletion_mark_iso_ts": None,
            "status": "active",
        }
    ]

    config = RagConfig(
        lifecycle_state_path=str(state_path),
        freshness_max_age_days=10,
        freshness_missing_ts_policy="exclude",
    )

    results, diagnostics = retrieve_chunks_with_diagnostics(
        "policy",
        chunks,
        config,
        {"terms": {}, "intent_groups": {}},
    )
    assert not results
    assert diagnostics["filtered_freshness_missing_timestamp"] == 1


def test_freshness_invalid_timestamp_policy_exclude_filters_chunk(tmp_path: Path) -> None:
    state_path = tmp_path / "lifecycle-state.json"
    chunks = [
        {
            "chunk_id": "orphan:0",
            "source_unit_id": "su_invalid_ts",
            "source": str(tmp_path / "orphan.txt"),
            "text": "policy note",
            "doc_type": "policy",
            "domain_area": "unknown",
            "is_tabular": False,
            "content_fingerprint": "abc",
            "ingestion_iso_ts": "not-a-timestamp",
            "last_upsert_iso_ts": "also-bad",
            "deletion_mark_iso_ts": None,
            "status": "active",
        }
    ]

    config = RagConfig(
        lifecycle_state_path=str(state_path),
        freshness_max_age_days=10,
        freshness_invalid_ts_policy="exclude",
    )

    results, diagnostics = retrieve_chunks_with_diagnostics(
        "policy",
        chunks,
        config,
        {"terms": {}, "intent_groups": {}},
    )
    assert not results
    assert diagnostics["filtered_freshness_invalid_timestamp"] == 1