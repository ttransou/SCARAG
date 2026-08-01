from __future__ import annotations

import json
from pathlib import Path

from scarag.config import RagConfig
from scarag.pipeline import build_chunk_index, retrieve_via_interface


def test_profile_doc_type_taxonomy_path_drives_inference(tmp_path: Path, monkeypatch) -> None:
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
        "default_doc_type": "unknown",
        "source_overrides": [{"contains": ["kb-article"], "doc_type": "faq"}],
        "doc_types": {
            "faq": {"patterns": ["faq", "frequently asked"]},
            "policy": {"patterns": ["policy"]},
        },
    }
    (config_dir / "doc_type_taxonomy.json").write_text(json.dumps(taxonomy_payload), encoding="utf-8")

    profile_payload = {
        "profile_id": "default",
        "taxonomy": {
            "concepts_path": "config/ontology.json",
            "doc_type_taxonomy_path": "config/doc_type_taxonomy.json",
        },
    }
    (profiles_dir / "default.json").write_text(json.dumps(profile_payload), encoding="utf-8")

    monkeypatch.chdir(tmp_path)
    config = RagConfig.from_profile("default", lifecycle_state_path=str(tmp_path / "state.json"))

    chunks = build_chunk_index(
        [
            {
                "source": str(tmp_path / "kb-article-001.txt"),
                "text": "Internal article body without obvious type keywords.",
            }
        ],
        config,
    )

    assert chunks
    assert chunks[0]["doc_type"] == "faq"


def test_profile_doc_type_preference_overrides_ranking(tmp_path: Path, monkeypatch) -> None:
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
        "default_doc_type": "unknown",
        "doc_types": {
            "faq": {"patterns": ["faq"]},
            "policy": {"patterns": ["policy"]},
        },
    }
    (config_dir / "doc_type_taxonomy.json").write_text(json.dumps(taxonomy_payload), encoding="utf-8")

    profile_payload = {
        "profile_id": "default",
        "retrieval": {
            "preferred_doc_types": ["faq"],
            "lower_priority_doc_types": ["policy"],
        },
        "taxonomy": {
            "concepts_path": "config/ontology.json",
            "doc_type_taxonomy_path": "config/doc_type_taxonomy.json",
        },
    }
    (profiles_dir / "default.json").write_text(json.dumps(profile_payload), encoding="utf-8")

    monkeypatch.chdir(tmp_path)
    config = RagConfig.from_profile(
        "default",
        lifecycle_state_path=str(tmp_path / "state.json"),
        retrieval_backend="lexical",
        min_retrieval_score=0.0,
    )

    chunks = build_chunk_index(
        [
            {
                "source": str(tmp_path / "faq.txt"),
                "text": "alpha",
                "doc_type": "faq",
            },
            {
                "source": str(tmp_path / "policy.txt"),
                "text": "alpha",
                "doc_type": "policy",
            },
        ],
        config,
    )

    response = retrieve_via_interface("alpha", chunks, config, {"terms": {}, "intent_groups": {}})

    assert response.ranked_chunks
    assert response.ranked_chunks[0]["doc_type"] == "faq"
