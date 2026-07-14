from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from scarag.config import RagConfig


@dataclass(frozen=True)
class RetrievalRequest:
    query: str
    chunks: list[dict[str, Any]]
    config: RagConfig
    thesaurus: dict[str, Any]


@dataclass(frozen=True)
class RetrievalResponse:
    ranked_chunks: list[dict[str, Any]]
    diagnostics: dict[str, int]


class Retriever(Protocol):
    """Contract boundary for retrieval backends (lexical, TF-IDF, vector, hybrid)."""

    def retrieve(self, request: RetrievalRequest) -> RetrievalResponse:
        ...
