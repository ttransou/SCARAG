from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


_REQUIRED_ONTOLOGY_CONCEPTS = {
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

_PREFERRED_DOC_TYPE_WEIGHT = 1.2
_LOWER_PRIORITY_DOC_TYPE_WEIGHT = 0.8


def _validate_ontology_path(concepts_path: str) -> None:
    ontology_path = Path(concepts_path)
    if not ontology_path.exists():
        raise ValueError(f"taxonomy.concepts_path does not exist: {concepts_path}")

    try:
        ontology_payload = json.loads(ontology_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"taxonomy.concepts_path is not valid JSON: {concepts_path}") from exc

    if not isinstance(ontology_payload, dict):
        raise ValueError(f"taxonomy.concepts_path must contain a JSON object: {concepts_path}")

    concepts = ontology_payload.get("concepts")
    relationships = ontology_payload.get("core_relationships")
    if not isinstance(concepts, list) or not isinstance(relationships, list):
        raise ValueError(
            "taxonomy.concepts_path must define list fields 'concepts' and 'core_relationships': "
            f"{concepts_path}"
        )

    concept_ids = {item.get("id") for item in concepts if isinstance(item, dict)}
    missing_concepts = sorted(_REQUIRED_ONTOLOGY_CONCEPTS - concept_ids)
    if missing_concepts:
        raise ValueError(
            "taxonomy.concepts_path is missing required SCARAG concepts "
            f"{missing_concepts}: {concepts_path}"
        )


def _as_str_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _normalize_weight_map(value: Any) -> dict[str, float]:
    if not isinstance(value, dict):
        return {}

    normalized: dict[str, float] = {}
    for key, raw_weight in value.items():
        key_text = str(key).strip().lower()
        if not key_text:
            continue
        try:
            weight = float(raw_weight)
        except (TypeError, ValueError):
            continue
        if weight <= 0:
            continue
        normalized[key_text] = weight
    return normalized


def _validate_doc_type_taxonomy_path(doc_type_taxonomy_path: str) -> None:
    taxonomy_path = Path(doc_type_taxonomy_path)
    if not taxonomy_path.exists():
        raise ValueError(f"taxonomy.doc_type_taxonomy_path does not exist: {doc_type_taxonomy_path}")

    try:
        taxonomy_payload = json.loads(taxonomy_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(
            f"taxonomy.doc_type_taxonomy_path is not valid JSON: {doc_type_taxonomy_path}"
        ) from exc

    if not isinstance(taxonomy_payload, dict):
        raise ValueError(
            "taxonomy.doc_type_taxonomy_path must contain a JSON object: "
            f"{doc_type_taxonomy_path}"
        )

    doc_types = taxonomy_payload.get("doc_types")
    if not isinstance(doc_types, dict):
        raise ValueError(
            "taxonomy.doc_type_taxonomy_path must define a 'doc_types' object: "
            f"{doc_type_taxonomy_path}"
        )

    if not doc_types:
        raise ValueError(
            "taxonomy.doc_type_taxonomy_path must define at least one doc type: "
            f"{doc_type_taxonomy_path}"
        )


@dataclass
class RagConfig:
    data_path: str = "data"
    thesaurus_path: str = "config/synonyms.json"
    profile: str = "default"
    generation_mode: str = "extractive"
    top_k: int = 5
    min_retrieval_score: float = 0.25
    retrieval_backend: str = "lexical"
    lexical_similarity_metric: str = "overlap"
    metadata_weighting_enabled: bool = True
    metadata_weight_rules: dict[str, dict[str, float]] = field(
        default_factory=lambda: {
            "doc_type": {
                "policy": 1.1,
                "procedure": 1.1,
                "report": 1.1,
                "faq": 1.1,
            }
        }
    )
    hybrid_rrf_k: int = 60
    boilerplate_penalty_enabled: bool = True
    boilerplate_penalty_strength: float = 0.25
    boilerplate_penalty_min_factor: float = 0.4
    table_aware_boost_enabled: bool = True
    table_intent_base_boost: float = 0.2
    table_header_match_boost: float = 0.2
    table_row_match_boost: float = 0.15
    retrieval_diagnostics_mode: str = "off"
    retrieval_diagnostics_top_n: int = 5
    vector_backend_adapter: str = "hashing"
    vector_similarity_metric: str = "cosine"
    vector_dimension: int = 256
    vector_use_char_ngrams: bool = True
    vector_char_ngram_min: int = 3
    vector_char_ngram_max: int = 5
    chunk_size: int = 120
    overlap: int = 20
    min_chunk_words: int = 40
    cohesion_threshold: float = 0.0
    table_chunk_rows: int = 25
    table_overlap_rows: int = 5
    lifecycle_state_path: str = "data/.scarag_lifecycle_state.json"
    exclude_soft_deleted: bool = True
    status_allow_list: list[str] = field(default_factory=list)
    status_deny_list: list[str] = field(default_factory=list)
    freshness_max_age_days: int | None = None
    freshness_use_last_upsert_first: bool = True
    freshness_missing_ts_policy: str = "include"
    freshness_invalid_ts_policy: str = "include"
    lifecycle_require_persisted_record: bool = False
    lifecycle_skip_unchanged: bool = False
    lifecycle_audit_logging_enabled: bool = False
    lifecycle_audit_log_path: str = "data/.scarag_lifecycle_audit.jsonl"
    ingestion_persist_lifecycle_state: bool = True
    chunk_include_document_level_details: bool = False
    confidence_temporal_decay_enabled: bool = True
    confidence_temporal_decay_half_life_days: float = 365.0
    confidence_temporal_decay_floor: float = 0.35
    confidence_intent_adjustment_enabled: bool = True
    confidence_intent_match_boost: float = 0.1
    confidence_intent_mismatch_penalty: float = 0.25
    confidence_intent_adjustment_floor: float = 0.7
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_profile(cls, profile: str, **overrides: Any) -> "RagConfig":
        config = cls(profile=profile)
        profile_path = Path("profiles") / f"{profile}.json"
        if profile_path.exists():
            profile_payload = json.loads(profile_path.read_text(encoding="utf-8"))
            if isinstance(profile_payload, dict):
                config.metadata = profile_payload

                taxonomy_overlay = profile_payload.get("taxonomy")
                if isinstance(taxonomy_overlay, dict):
                    concepts_path = taxonomy_overlay.get("concepts_path")
                    if isinstance(concepts_path, str) and concepts_path.strip():
                        _validate_ontology_path(concepts_path.strip())

                    doc_type_taxonomy_path = taxonomy_overlay.get("doc_type_taxonomy_path")
                    if isinstance(doc_type_taxonomy_path, str) and doc_type_taxonomy_path.strip():
                        _validate_doc_type_taxonomy_path(doc_type_taxonomy_path.strip())

                synonyms_path = profile_payload.get("synonyms_path")
                if isinstance(synonyms_path, str) and synonyms_path.strip():
                    config.thesaurus_path = synonyms_path.strip()

                lifecycle_overlay = profile_payload.get("lifecycle")
                if isinstance(lifecycle_overlay, dict):
                    preferred_statuses = _as_str_list(lifecycle_overlay.get("preferred_statuses"))
                    if preferred_statuses:
                        config.status_allow_list = preferred_statuses

                    excluded_statuses = _as_str_list(lifecycle_overlay.get("excluded_statuses"))
                    if excluded_statuses:
                        config.status_deny_list = excluded_statuses

                    freshness_days_default = lifecycle_overlay.get("freshness_days_default")
                    if isinstance(freshness_days_default, (int, float)) and not isinstance(
                        freshness_days_default,
                        bool,
                    ):
                        config.freshness_max_age_days = int(freshness_days_default)
                    elif freshness_days_default is None:
                        config.freshness_max_age_days = None

                    missing_timestamp_policy = lifecycle_overlay.get("missing_timestamp_policy")
                    if isinstance(missing_timestamp_policy, str) and missing_timestamp_policy.strip():
                        config.freshness_missing_ts_policy = missing_timestamp_policy.strip()

                retrieval_overlay = profile_payload.get("retrieval")
                if isinstance(retrieval_overlay, dict):
                    preferred_doc_types = {
                        item.lower() for item in _as_str_list(retrieval_overlay.get("preferred_doc_types"))
                    }
                    lower_priority_doc_types = {
                        item.lower()
                        for item in _as_str_list(retrieval_overlay.get("lower_priority_doc_types"))
                    }

                    existing_rules = config.metadata_weight_rules if isinstance(config.metadata_weight_rules, dict) else {}
                    merged_rules: dict[str, dict[str, float]] = {
                        key: _normalize_weight_map(value)
                        for key, value in existing_rules.items()
                        if isinstance(key, str)
                    }
                    doc_type_rules = dict(merged_rules.get("doc_type", {}))

                    for doc_type in preferred_doc_types:
                        current = doc_type_rules.get(doc_type, 1.0)
                        doc_type_rules[doc_type] = max(current, _PREFERRED_DOC_TYPE_WEIGHT)

                    for doc_type in lower_priority_doc_types:
                        current = doc_type_rules.get(doc_type, 1.0)
                        doc_type_rules[doc_type] = min(current, _LOWER_PRIORITY_DOC_TYPE_WEIGHT)

                    if doc_type_rules:
                        merged_rules["doc_type"] = doc_type_rules
                        config.metadata_weight_rules = merged_rules
            else:
                config.metadata = {}
        for key, value in overrides.items():
            setattr(config, key, value)
        return config
