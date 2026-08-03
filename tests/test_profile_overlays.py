from __future__ import annotations

import json
from pathlib import Path

from scarag.config import RagConfig
from scarag.pipeline import build_chunk_index


def test_from_profile_maps_synonyms_and_lifecycle_overlay(tmp_path: Path, monkeypatch) -> None:
    profiles_dir = tmp_path / "profiles"
    profiles_dir.mkdir(parents=True, exist_ok=True)
    profile_payload = {
        "profile_id": "default",
        "display_name": "Default",
        "synonyms_path": "config/custom-synonyms.json",
        "lifecycle": {
            "preferred_statuses": ["active", "pending_review"],
            "excluded_statuses": ["retired", "deleted"],
            "freshness_days_default": 45,
            "missing_timestamp_policy": "exclude",
        },
    }
    (profiles_dir / "default.json").write_text(json.dumps(profile_payload), encoding="utf-8")

    monkeypatch.chdir(tmp_path)
    config = RagConfig.from_profile("default")

    assert config.metadata == profile_payload
    assert config.thesaurus_path == "config/custom-synonyms.json"
    assert config.status_allow_list == ["active", "pending_review"]
    assert config.status_deny_list == ["retired", "deleted"]
    assert config.freshness_max_age_days == 45
    assert config.freshness_missing_ts_policy == "exclude"


def test_from_profile_overrides_take_precedence(tmp_path: Path, monkeypatch) -> None:
    profiles_dir = tmp_path / "profiles"
    profiles_dir.mkdir(parents=True, exist_ok=True)
    profile_payload = {
        "profile_id": "default",
        "synonyms_path": "config/synonyms-from-profile.json",
        "lifecycle": {
            "preferred_statuses": ["active"],
            "excluded_statuses": ["retired"],
            "freshness_days_default": 10,
            "missing_timestamp_policy": "include",
        },
    }
    (profiles_dir / "default.json").write_text(json.dumps(profile_payload), encoding="utf-8")

    monkeypatch.chdir(tmp_path)
    config = RagConfig.from_profile(
        "default",
        thesaurus_path="config/synonyms-from-override.json",
        freshness_max_age_days=7,
        freshness_missing_ts_policy="exclude",
    )

    assert config.thesaurus_path == "config/synonyms-from-override.json"
    assert config.freshness_max_age_days == 7
    assert config.freshness_missing_ts_policy == "exclude"


def test_from_profile_raises_for_missing_ontology_path(tmp_path: Path, monkeypatch) -> None:
    profiles_dir = tmp_path / "profiles"
    profiles_dir.mkdir(parents=True, exist_ok=True)
    profile_payload = {
        "profile_id": "default",
        "taxonomy": {
            "concepts_path": "config/missing_ontology.json",
        },
    }
    (profiles_dir / "default.json").write_text(json.dumps(profile_payload), encoding="utf-8")

    monkeypatch.chdir(tmp_path)
    try:
        RagConfig.from_profile("default")
        assert False, "Expected ValueError for missing ontology path"
    except ValueError as exc:
        assert "taxonomy.concepts_path does not exist" in str(exc)


def test_from_profile_accepts_valid_ontology_path(tmp_path: Path, monkeypatch) -> None:
    profiles_dir = tmp_path / "profiles"
    config_dir = tmp_path / "config"
    profiles_dir.mkdir(parents=True, exist_ok=True)
    config_dir.mkdir(parents=True, exist_ok=True)

    ontology_payload = {
        "concepts": [
            {"id": "Source"},
            {"id": "SourceUnit"},
            {"id": "EvidenceUnit"},
            {"id": "DocumentType"},
            {"id": "LifecycleStatus"},
            {"id": "Provenance"},
            {"id": "ConfidenceSignal"},
            {"id": "Citation"},
            {"id": "DomainProfile"},
            {"id": "Concept"},
        ],
        "core_relationships": [],
    }
    (config_dir / "ontology.json").write_text(json.dumps(ontology_payload), encoding="utf-8")

    profile_payload = {
        "profile_id": "default",
        "taxonomy": {
            "concepts_path": "config/ontology.json",
        },
    }
    (profiles_dir / "default.json").write_text(json.dumps(profile_payload), encoding="utf-8")

    monkeypatch.chdir(tmp_path)
    config = RagConfig.from_profile("default")
    assert config.profile == "default"


def test_from_profile_raises_for_missing_doc_type_taxonomy_path(tmp_path: Path, monkeypatch) -> None:
    profiles_dir = tmp_path / "profiles"
    config_dir = tmp_path / "config"
    profiles_dir.mkdir(parents=True, exist_ok=True)
    config_dir.mkdir(parents=True, exist_ok=True)

    ontology_payload = {
        "concepts": [
            {"id": "Source"},
            {"id": "SourceUnit"},
            {"id": "EvidenceUnit"},
            {"id": "DocumentType"},
            {"id": "LifecycleStatus"},
            {"id": "Provenance"},
            {"id": "ConfidenceSignal"},
            {"id": "Citation"},
            {"id": "DomainProfile"},
            {"id": "Concept"},
        ],
        "core_relationships": [],
    }
    (config_dir / "ontology.json").write_text(json.dumps(ontology_payload), encoding="utf-8")

    profile_payload = {
        "profile_id": "default",
        "taxonomy": {
            "concepts_path": "config/ontology.json",
            "doc_type_taxonomy_path": "config/missing_doc_types.json",
        },
    }
    (profiles_dir / "default.json").write_text(json.dumps(profile_payload), encoding="utf-8")

    monkeypatch.chdir(tmp_path)
    try:
        RagConfig.from_profile("default")
        assert False, "Expected ValueError for missing doc type taxonomy path"
    except ValueError as exc:
        assert "taxonomy.doc_type_taxonomy_path does not exist" in str(exc)


def test_from_profile_applies_doc_type_retrieval_overlay_weights(tmp_path: Path, monkeypatch) -> None:
    profiles_dir = tmp_path / "profiles"
    config_dir = tmp_path / "config"
    profiles_dir.mkdir(parents=True, exist_ok=True)
    config_dir.mkdir(parents=True, exist_ok=True)

    ontology_payload = {
        "concepts": [
            {"id": "Source"},
            {"id": "SourceUnit"},
            {"id": "EvidenceUnit"},
            {"id": "DocumentType"},
            {"id": "LifecycleStatus"},
            {"id": "Provenance"},
            {"id": "ConfidenceSignal"},
            {"id": "Citation"},
            {"id": "DomainProfile"},
            {"id": "Concept"},
        ],
        "core_relationships": [],
    }
    (config_dir / "ontology.json").write_text(json.dumps(ontology_payload), encoding="utf-8")

    taxonomy_payload = {
        "doc_types": {
            "faq": {"patterns": ["faq"]},
            "policy": {"patterns": ["policy"]},
        }
    }
    (config_dir / "doc_types.json").write_text(json.dumps(taxonomy_payload), encoding="utf-8")

    profile_payload = {
        "profile_id": "default",
        "retrieval": {
            "preferred_doc_types": ["faq"],
            "lower_priority_doc_types": ["policy"],
        },
        "taxonomy": {
            "concepts_path": "config/ontology.json",
            "doc_type_taxonomy_path": "config/doc_types.json",
        },
    }
    (profiles_dir / "default.json").write_text(json.dumps(profile_payload), encoding="utf-8")

    monkeypatch.chdir(tmp_path)
    config = RagConfig.from_profile("default")

    doc_type_rules = config.metadata_weight_rules.get("doc_type", {})
    assert float(doc_type_rules.get("faq", 0.0)) >= 1.2
    assert float(doc_type_rules.get("policy", 0.0)) <= 0.8


def test_humanities_profile_loads_with_humanities_overlays() -> None:
    config = RagConfig.from_profile("humanities")

    assert config.metadata["profile_id"] == "humanities"
    assert config.thesaurus_path == "config/humanities_synonyms.json"
    assert "note" in config.metadata["retrieval"]["preferred_doc_types"]
    assert "provenance" in config.metadata["retrieval"]["boost_terms"]
    assert "reviewed" in config.status_allow_list
    assert "draft" in config.status_deny_list


def test_humanities_taxonomy_infers_art_history_document_type() -> None:
    config = RagConfig.from_profile("humanities")

    chunks = build_chunk_index(
        [
            {
                "source": "example/painting-catalog-entry.txt",
                "text": "A catalog entry for a Renaissance altarpiece with provenance and attribution notes.",
            }
        ],
        config,
    )

    assert chunks
    assert chunks[0]["doc_type"] == "art_work"
