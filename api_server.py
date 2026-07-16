from __future__ import annotations

from typing import Any

from scarag.confidence import resolve_confidence
from scarag.config import RagConfig
from scarag.generation.answerer import generate_answer_result
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
_CONTRACT_VERSION = "1.0"


def _select_generation_citations(
    context: list[dict[str, Any]],
    cited_chunk_ids: list[str],
) -> list[dict[str, Any]]:
    if not cited_chunk_ids:
        return []

    cited_id_set = {str(value).strip() for value in cited_chunk_ids if str(value).strip()}
    ordered_context: list[dict[str, Any]] = []
    seen: set[str] = set()
    for chunk in context:
        chunk_id = str(chunk.get("chunk_id", "")).strip()
        if not chunk_id or chunk_id not in cited_id_set or chunk_id in seen:
            continue
        ordered_context.append(chunk)
        seen.add(chunk_id)
    return ordered_context


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
        "contract_version": _CONTRACT_VERSION,
        "chunks_indexed": len(chunks),
    }


@app.post("/api/chat")
def chat(payload: dict[str, Any]) -> dict[str, Any]:
    query = str(payload.get("query", "")).strip()
    if not query:
        response_text = "Please provide a query."
        return {
            "contract_version": _CONTRACT_VERSION,
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
    generation_result = generate_answer_result(
        query,
        enforced_context,
        mode=_CONFIG.generation_mode,
        tabular_intent=tabular_query,
    )
    response_text = generation_result.text

    citation_context = _select_generation_citations(enforced_context, generation_result.cited_chunk_ids)
    raw_citations = [_to_citation(chunk, index) for index, chunk in enumerate(citation_context)]
    citations, citation_enforcement = filter_complete_citations(raw_citations, enforced_context)
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
        "contract_version": _CONTRACT_VERSION,
        "message": {
            "text": response_text,
            "citations_summary": summary,
            "tabular_trace": tabular_trace,
            "provenance_validation": provenance_validation,
            "generation": {
                "grounding_policy": generation_result.grounding_policy,
                "abstained": generation_result.abstained,
                "reason_code": generation_result.reason_code,
                "used_context_count": generation_result.used_context_count,
                "cited_chunk_ids": generation_result.cited_chunk_ids,
            },
        },
        "citations": visible,
        "collapsed_citations": collapsed,
        "confidence": confidence,
        "answer": response_text,
    }
