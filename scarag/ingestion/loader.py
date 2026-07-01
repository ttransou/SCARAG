from __future__ import annotations

import json
import re
import zipfile
from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup
from docx import Document as DocxDocument
from pptx import Presentation as PptxPresentation
from pypdf import PdfReader
from openpyxl import load_workbook


def _read_text_file(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def _parse_html(path: Path) -> str:
    html = _read_text_file(path)
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style"]):
        tag.decompose()
    return "\n\n".join(part.strip() for part in re.split(r"\n{2,}", soup.get_text("\n", strip=True)) if part.strip())


def _parse_docx(path: Path) -> str:
    document = DocxDocument(path)
    return "\n".join(paragraph.text.strip() for paragraph in document.paragraphs if paragraph.text.strip())


def _parse_pdf(path: Path) -> str:
    reader = PdfReader(str(path))
    pages = [page.extract_text() or "" for page in reader.pages]
    return "\n\n".join(page.strip() for page in pages if page.strip())


def _parse_pptx(path: Path) -> str:
    presentation = PptxPresentation(path)
    slides = []
    for slide in presentation.slides:
        texts = [shape.text.strip() for shape in slide.shapes if getattr(shape, "text", "").strip()]
        if texts:
            slides.append("\n".join(texts))
    return "\n\n".join(slides)


def _parse_xlsx(path: Path) -> str:
    workbook = load_workbook(path, read_only=True, data_only=True)
    sheets = []
    for sheet in workbook.worksheets:
        rows = []
        for row in sheet.iter_rows(values_only=True):
            cleaned = [str(value).strip() for value in row if value is not None and str(value).strip()]
            if cleaned:
                rows.append(" | ".join(cleaned))
        if rows:
            sheets.append("\n".join(rows))
    return "\n\n".join(sheets)


def _parse_json(path: Path) -> str:
    data = json.loads(_read_text_file(path))
    if isinstance(data, dict):
        return "\n".join(f"{key}: {value}" for key, value in data.items())
    if isinstance(data, list):
        return "\n".join(json.dumps(item, ensure_ascii=False) for item in data)
    return str(data)


def _parse_csv(path: Path) -> str:
    return _read_text_file(path)


def _parse_mhtml(path: Path) -> str:
    content = _read_text_file(path)
    if "Content-Type: text/html" in content:
        match = re.search(r"Content-Type: text/html[^\n]*\n\n(.*)", content, re.DOTALL)
        if match:
            html = match.group(1)
            soup = BeautifulSoup(html, "html.parser")
            return soup.get_text("\n", strip=True)
    return content


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
        if not path.is_file():
            continue

        suffix = path.suffix.lower()
        if suffix in {".txt", ".md", ".json", ".csv", ".mhtml", ".mht"}:
            parser = {
                ".json": _parse_json,
                ".csv": _parse_csv,
                ".mhtml": _parse_mhtml,
                ".mht": _parse_mhtml,
            }.get(suffix)
            text = parser(path) if parser else _read_text_file(path)
            documents.append({"source": str(path), "text": text, "doc_type": "unknown"})
            continue

        if suffix == ".html" or suffix == ".htm":
            documents.append(
                {"source": str(path), "text": _parse_html(path), "doc_type": "unknown"}
            )
            continue

        if suffix == ".docx":
            documents.append(
                {"source": str(path), "text": _parse_docx(path), "doc_type": "unknown"}
            )
            continue

        if suffix == ".pdf":
            documents.append(
                {"source": str(path), "text": _parse_pdf(path), "doc_type": "unknown"}
            )
            continue

        if suffix == ".pptx":
            documents.append(
                {"source": str(path), "text": _parse_pptx(path), "doc_type": "unknown"}
            )
            continue

        if suffix == ".xlsx" or suffix == ".xls":
            documents.append(
                {"source": str(path), "text": _parse_xlsx(path), "doc_type": "unknown"}
            )
            continue

    return documents
