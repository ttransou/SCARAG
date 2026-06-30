from __future__ import annotations

from typing import Any

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


@app.get("/api/health")
def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "service": "SCARAG",
        "mode": "reference",
    }


@app.post("/api/chat")
def chat(payload: dict[str, Any]) -> dict[str, Any]:
    query = str(payload.get("query", "")).strip()
    response_text = f"SCARAG received your query: {query or 'empty query'}"
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
