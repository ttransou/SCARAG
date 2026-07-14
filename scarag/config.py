from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class RagConfig:
    data_path: str = "data"
    thesaurus_path: str = "config/synonyms.json"
    profile: str = "default"
    generation_mode: str = "extractive"
    top_k: int = 5
    min_retrieval_score: float = 0.25
    retrieval_backend: str = "lexical"
    hybrid_rrf_k: int = 60
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
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_profile(cls, profile: str, **overrides: Any) -> "RagConfig":
        config = cls(profile=profile)
        profile_path = Path("profiles") / f"{profile}.json"
        if profile_path.exists():
            import json

            config.metadata = json.loads(profile_path.read_text(encoding="utf-8"))
        for key, value in overrides.items():
            setattr(config, key, value)
        return config
