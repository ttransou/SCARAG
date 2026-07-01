import zipfile
from pathlib import Path
from tempfile import TemporaryDirectory

from pptx import Presentation as PptxPresentation
from openpyxl import Workbook

import tomllib

from scarag.ingestion.loader import load_documents


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_document_parser_dependencies_are_declared() -> None:
    requirements = (REPO_ROOT / "requirements.txt").read_text(encoding="utf-8")
    pyproject = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))

    declared_requirements = pyproject["project"]["dependencies"]

    for package in [
        "pypdf",
        "pdfplumber",
        "python-docx",
        "python-pptx",
        "openpyxl",
        "beautifulsoup4",
        "lxml",
    ]:
        assert package in requirements
        assert any(package in dependency for dependency in declared_requirements)


def test_loader_handles_json_csv_and_mhtml_documents() -> None:
    with TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        (temp_path / "sample.json").write_text(
            '{"title": "Example", "value": 42}', encoding="utf-8"
        )
        (temp_path / "sample.csv").write_text(
            "name,value\nalpha,1\n", encoding="utf-8"
        )
        (temp_path / "sample.mhtml").write_bytes(
            b"From: sender@example.com\n"
            b"Content-Type: multipart/alternative; boundary=boundary\n\n"
            b"--boundary\n"
            b"Content-Type: text/plain; charset=utf-8\n\n"
            b"Plain text body\n"
            b"--boundary\n"
            b"Content-Type: text/html; charset=utf-8\n\n"
            b"<html><body><p>MHTML body</p></body></html>\n"
            b"--boundary--\n"
        )

        documents = load_documents(temp_path)

    assert len(documents) == 3
    assert any(doc["source"].endswith("sample.json") for doc in documents)
    assert any(doc["source"].endswith("sample.csv") for doc in documents)
    assert any(doc["source"].endswith("sample.mhtml") for doc in documents)
    assert any("MHTML body" in doc["text"] for doc in documents)


def test_loader_parses_html_and_docx_content() -> None:
    with TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        (temp_path / "sample.html").write_text(
            "<html><body><h1>Heading</h1><p>HTML paragraph</p></body></html>",
            encoding="utf-8",
        )

        docx_path = temp_path / "sample.docx"
        with zipfile.ZipFile(docx_path, "w") as archive:
            archive.writestr(
                "[Content_Types].xml",
                """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
                <Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
                  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
                  <Default Extension="xml" ContentType="application/xml"/>
                  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
                </Types>""",
            )
            archive.writestr(
                "_rels/.rels",
                """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
                <Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
                  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
                </Relationships>""",
            )
            archive.writestr(
                "word/document.xml",
                """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
                <w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
                  <w:body>
                    <w:p><w:r><w:t>Docx paragraph</w:t></w:r></w:p>
                  </w:body>
                </w:document>""",
            )

        documents = load_documents(temp_path)

    assert len(documents) == 2
    html_doc = next(doc for doc in documents if doc["source"].endswith("sample.html"))
    docx_doc = next(doc for doc in documents if doc["source"].endswith("sample.docx"))
    assert "HTML paragraph" in html_doc["text"]
    assert "Docx paragraph" in docx_doc["text"]


def test_loader_parses_pptx_and_xlsx_content() -> None:
    with TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        pptx_path = temp_path / "sample.pptx"
        presentation = PptxPresentation()
        slide = presentation.slides.add_slide(presentation.slide_layouts[1])
        slide.shapes.title.text = "Slide title"
        slide.placeholders[1].text = "Slide body"
        presentation.save(pptx_path)

        workbook = Workbook()
        sheet = workbook.active
        sheet.append(["Name", "Value"])
        sheet.append(["Alpha", 1])
        workbook.save(temp_path / "sample.xlsx")

        documents = load_documents(temp_path)

    assert len(documents) == 2
    pptx_doc = next(doc for doc in documents if doc["source"].endswith("sample.pptx"))
    xlsx_doc = next(doc for doc in documents if doc["source"].endswith("sample.xlsx"))
    assert "Slide title" in pptx_doc["text"]
    assert "Slide body" in pptx_doc["text"]
    assert "Name" in xlsx_doc["text"]
    assert "Alpha" in xlsx_doc["text"]
