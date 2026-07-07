from __future__ import annotations

from typing import Any

from scarag.config import RagConfig
from scarag.generation.answerer import generate_answer
from scarag.ingestion.loader import load_documents
from scarag.pipeline import build_chunk_index, is_tabular_intent, load_thesaurus, retrieve_chunks

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


def _get_chunks() -> list[dict[str, Any]]:
    global _CHUNK_CACHE
    if _CHUNK_CACHE is None:
        documents = load_documents(_CONFIG.data_path)
        _CHUNK_CACHE = build_chunk_index(documents, _CONFIG)
    return _CHUNK_CACHE


def _to_citation(chunk: dict[str, Any], rank: int) -> dict[str, Any]:
    source = str(chunk.get("source", "unknown"))
    return {
        "id": str(chunk.get("chunk_id", f"chunk-{rank}")),
        "title": source.split("/")[-1],
        "document": source,
        "snippet": str(chunk.get("text", ""))[:280],
        "score": chunk.get("score", 0.0),
        "chunk_id": chunk.get("chunk_id"),
        "doc_type": chunk.get("doc_type", "unknown"),
    }


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
            "answer": response_text,
        }

    chunks = _get_chunks()
    ranked_chunks = retrieve_chunks(query, chunks, _CONFIG, _THESAURUS)
    tabular_query = is_tabular_intent(query, _THESAURUS)
    response_text = generate_answer(
        query,
        ranked_chunks,
        mode=_CONFIG.generation_mode,
        tabular_intent=tabular_query,
    )

    citations = [_to_citation(chunk, index) for index, chunk in enumerate(ranked_chunks)]
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

    confidence = "high" if citations else "low"
    if tabular_query and not any(bool(chunk.get("is_tabular")) for chunk in ranked_chunks):
        confidence = "abstain"

    return {
        "message": {
            "text": response_text,
            "citations_summary": summary,
        },
        "citations": visible,
        "collapsed_citations": collapsed,
        "confidence": confidence,
        "answer": response_text,
    }
