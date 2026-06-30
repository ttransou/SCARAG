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
    chunk_size: int = 120
    overlap: int = 20
    min_chunk_words: int = 40
    cohesion_threshold: float = 0.0
    table_chunk_rows: int = 25
    table_overlap_rows: int = 5
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
