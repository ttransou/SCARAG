from __future__ import annotations

from pathlib import Path
from typing import Any


def load_documents(data_path: str | Path) -> list[dict[str, Any]]:
    """Load a simple list of document-like records from a folder.

    The repository README describes a richer ingestion pipeline, but this
    reference implementation keeps the interface lightweight until real parsers
    are added.
    """
    root = Path(data_path)
    if not root.exists():
        return []

    documents: list[dict[str, Any]] = []
    for path in sorted(root.rglob("*")):
        if path.is_file() and path.suffix.lower() in {".txt", ".md", ".json", ".csv"}:
            documents.append(
                {
                    "source": str(path),
                    "text": path.read_text(encoding="utf-8", errors="ignore"),
                    "doc_type": "unknown",
                }
            )
    return documents
