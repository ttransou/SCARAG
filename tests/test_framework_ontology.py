from __future__ import annotations

import json
from pathlib import Path


def test_framework_ontology_contains_minimum_concepts_and_relationships() -> None:
    ontology_path = Path("config/scarag_base_ontology.json")
    assert ontology_path.exists()

    payload = json.loads(ontology_path.read_text(encoding="utf-8"))
    concepts = payload.get("concepts", [])
    relationships = payload.get("core_relationships", [])

    concept_ids = {item.get("id") for item in concepts if isinstance(item, dict)}
    expected_concepts = {
        "Source",
        "SourceUnit",
        "EvidenceUnit",
        "DocumentType",
        "LifecycleStatus",
        "Provenance",
        "ConfidenceSignal",
        "Citation",
        "DomainProfile",
        "Concept",
    }
    assert expected_concepts.issubset(concept_ids)

    edge_set = {
        (item.get("subject"), item.get("predicate"), item.get("object"))
        for item in relationships
        if isinstance(item, dict)
    }
    expected_edges = {
        ("Source", "contains", "SourceUnit"),
        ("SourceUnit", "produces", "EvidenceUnit"),
        ("EvidenceUnit", "carries", "Metadata"),
        ("EvidenceUnit", "has", "LifecycleStatus"),
        ("EvidenceUnit", "has", "Provenance"),
        ("EvidenceUnit", "may_support", "Citation"),
        ("EvidenceUnit", "may_contribute_to", "Answer"),
        ("DomainProfile", "guides", "retrieval_lifecycle_confidence_vocabulary_behavior"),
    }
    assert expected_edges.issubset(edge_set)


def test_default_profile_points_to_framework_ontology() -> None:
    profile_payload = json.loads(Path("profiles/default.json").read_text(encoding="utf-8"))
    taxonomy = profile_payload.get("taxonomy", {})
    assert taxonomy.get("concepts_path") == "config/scarag_base_ontology.json"
