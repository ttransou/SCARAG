from __future__ import annotations

from typing import Any

from scarag.confidence import resolve_confidence
from scarag.config import RagConfig
from scarag.generation.answerer import generate_answer
from scarag.ingestion.loader import load_documents
from scarag.pipeline import build_chunk_index, is_tabular_intent, load_thesaurus, retrieve_chunks
from scarag.provenance import (
    filter_complete_citations,
    filter_complete_source_chunks,
    validate_provenance,
)
from scarag.tabular_grounding import apply_tabular_grounding

try:
    from fastapi import FastAPI
except ImportError:  # pragma: no cover - fallback for lightweight environments
    class FastAPI:  # type: ignore[override]
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            self.routes: list[tuple[str, Any]] = []

        def get(self, path: str):
            def decorator(func):
                self.routes.append((path, func))
                return func

            return decorator

        def post(self, path: str):
            def decorator(func):
                self.routes.append((path, func))
                return func

            return decorator


app = FastAPI(title="SCARAG", version="0.1.0")

_CONFIG = RagConfig()
_THESAURUS = load_thesaurus(_CONFIG)
_CHUNK_CACHE: list[dict[str, Any]] | None = None
_ALLOWED_CONFIDENCE_LABELS = {"high", "low", "abstain"}


def _normalize_confidence_label(label: Any) -> str:
    normalized = str(label or "").strip().lower()
    if normalized in _ALLOWED_CONFIDENCE_LABELS:
        return normalized
    return "abstain"


def _get_chunks() -> list[dict[str, Any]]:
    global _CHUNK_CACHE
    if _CHUNK_CACHE is None:
        documents = load_documents(_CONFIG.data_path)
        _CHUNK_CACHE = build_chunk_index(documents, _CONFIG)
    return _CHUNK_CACHE


def _to_citation(chunk: dict[str, Any], rank: int) -> dict[str, Any]:
    source = str(chunk.get("source", "unknown"))
    citation = {
        "id": str(chunk.get("chunk_id", f"chunk-{rank}")),
        "title": source.split("/")[-1],
        "document": source,
        "snippet": str(chunk.get("text", ""))[:280],
        "score": chunk.get("score", 0.0),
        "chunk_id": chunk.get("chunk_id"),
        "doc_type": chunk.get("doc_type", "unknown"),
    }
    if bool(chunk.get("tabular_grounded")):
        citation["tabular_grounded"] = True
        citation["matched_row_count"] = int(chunk.get("matched_row_count", 0))
        citation["matched_terms"] = list(chunk.get("matched_terms", []))
    return citation


@app.get("/api/health")
def health() -> dict[str, Any]:
    chunks = _get_chunks()
    return {
        "status": "ok",
        "service": "SCARAG",
        "mode": _CONFIG.generation_mode,
        "chunks_indexed": len(chunks),
    }


@app.post("/api/chat")
def chat(payload: dict[str, Any]) -> dict[str, Any]:
    query = str(payload.get("query", "")).strip()
    if not query:
        response_text = "Please provide a query."
        return {
            "message": {
                "text": response_text,
                "citations_summary": {
                    "count": 0,
                    "total_count": 0,
                    "hidden_count": 0,
                    "label": "no citations",
                },
            },
            "citations": [],
            "collapsed_citations": [],
            "confidence": "abstain",
            "answer": response_text,
        }

    chunks = _get_chunks()
    ranked_chunks = retrieve_chunks(query, chunks, _CONFIG, _THESAURUS)
    tabular_query = is_tabular_intent(query, _THESAURUS)
    grounded_chunks, tabular_trace = apply_tabular_grounding(
        query,
        ranked_chunks,
        tabular_intent=tabular_query,
    )
    answer_context = grounded_chunks if tabular_query else ranked_chunks
    enforced_context, source_enforcement = filter_complete_source_chunks(answer_context)
    response_text = generate_answer(
        query,
        enforced_context,
        mode=_CONFIG.generation_mode,
        tabular_intent=tabular_query,
    )

    raw_citations = [_to_citation(chunk, index) for index, chunk in enumerate(enforced_context)]
    citations, citation_enforcement = filter_complete_citations(raw_citations)
    visible = citations[:3]
    collapsed = citations[3:]

    if not collapsed:
        collapsed = [citation for citation in visible if float(citation.get("score", 0.0)) < 0.5]
        visible = [citation for citation in visible if citation not in collapsed]

    summary = {
        "count": len(visible),
        "total_count": len(citations),
        "hidden_count": len(collapsed),
        "label": "citations available" if citations else "no citations",
    }
    provenance_validation = validate_provenance(enforced_context, citations)
    provenance_validation["enforcement"] = {
        "source_chunks": source_enforcement,
        "citations": citation_enforcement,
    }

    confidence_result = resolve_confidence(
        query,
        enforced_context,
        tabular_intent=tabular_query,
        thesaurus=_THESAURUS,
        temporal_decay_enabled=_CONFIG.confidence_temporal_decay_enabled,
        temporal_decay_half_life_days=_CONFIG.confidence_temporal_decay_half_life_days,
        temporal_decay_floor=_CONFIG.confidence_temporal_decay_floor,
        intent_adjustment_enabled=_CONFIG.confidence_intent_adjustment_enabled,
        intent_match_boost=_CONFIG.confidence_intent_match_boost,
        intent_mismatch_penalty=_CONFIG.confidence_intent_mismatch_penalty,
        intent_adjustment_floor=_CONFIG.confidence_intent_adjustment_floor,
    )
    confidence = _normalize_confidence_label(confidence_result.label)

    return {
        "message": {
            "text": response_text,
            "citations_summary": summary,
            "tabular_trace": tabular_trace,
            "provenance_validation": provenance_validation,
        },
        "citations": visible,
        "collapsed_citations": collapsed,
        "confidence": confidence,
        "answer": response_text,
    }
