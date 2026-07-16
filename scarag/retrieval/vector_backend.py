from __future__ import annotations

import hashlib
import math
import re
from dataclasses import dataclass
from typing import Protocol

_WHITESPACE_RE = re.compile(r"\s+")


class VectorEmbedder(Protocol):
    """Adapter boundary for vector embedding implementations."""

    def embed(self, text: str) -> list[float]:
        ...


@dataclass(frozen=True)
class HashingVectorEmbedder:
    """Deterministic dense vectorizer using hashed lexical and char-ngram features."""

    dimension: int = 256
    use_char_ngrams: bool = True
    char_ngram_min: int = 3
    char_ngram_max: int = 5

    def embed(self, text: str) -> list[float]:
        dims = max(16, int(self.dimension))
        vector = [0.0] * dims
        normalized = _normalize_text(text)
        if not normalized:
            return vector

        for token in normalized.split():
            _add_feature(vector, f"tok:{token}", 1.0)

        if self.use_char_ngrams:
            min_n = max(1, int(self.char_ngram_min))
            max_n = max(min_n, int(self.char_ngram_max))
            compact = normalized.replace(" ", "_")
            for n in range(min_n, max_n + 1):
                if len(compact) < n:
                    continue
                for index in range(0, len(compact) - n + 1):
                    ngram = compact[index : index + n]
                    _add_feature(vector, f"ch{n}:{ngram}", 0.35)

        return _l2_normalize(vector)


def cosine_similarity(left: list[float], right: list[float]) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0
    return sum(a * b for a, b in zip(left, right))


def _normalize_text(text: str) -> str:
    collapsed = _WHITESPACE_RE.sub(" ", str(text or "").strip().lower())
    return collapsed


def _hash_index(feature: str, dim: int) -> int:
    digest = hashlib.sha1(feature.encode("utf-8", errors="ignore")).digest()
    return int.from_bytes(digest[:8], byteorder="big", signed=False) % dim


def _add_feature(vector: list[float], feature: str, weight: float) -> None:
    if not vector:
        return
    index = _hash_index(feature, len(vector))
    vector[index] += float(weight)


def _l2_normalize(vector: list[float]) -> list[float]:
    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0.0:
        return vector
    return [value / norm for value in vector]
