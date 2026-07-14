from __future__ import annotations

from scarag.generation.answerer import generate_answer
from scarag.tabular_grounding import apply_tabular_grounding


def test_tabular_grounding_returns_only_matched_rows() -> None:
    chunks = [
        {
            "chunk_id": "table.csv:0",
            "source": "table.csv",
            "is_tabular": True,
            "text": "name | quarter | value\nalpha | q1 | 10\nbeta | q2 | 20",
        },
        {
            "chunk_id": "note.txt:0",
            "source": "note.txt",
            "is_tabular": False,
            "text": "policy notes",
        },
    ]

    grounded, trace = apply_tabular_grounding("alpha q1", chunks, tabular_intent=True)

    assert len(grounded) == 1
    assert grounded[0]["tabular_grounded"] is True
    assert grounded[0]["matched_row_count"] >= 1
    assert trace["matched_chunks"] == 1
    assert trace["matched_rows"] >= 1


def test_tabular_grounding_returns_empty_when_no_row_match() -> None:
    chunks = [
        {
            "chunk_id": "table.csv:0",
            "source": "table.csv",
            "is_tabular": True,
            "text": "name | quarter | value\nalpha | q1 | 10\nbeta | q2 | 20",
        }
    ]

    grounded, trace = apply_tabular_grounding("gamma q4", chunks, tabular_intent=True)

    assert grounded == []
    assert trace["reason"] == "no_matched_rows"


def test_generate_answer_abstains_without_matched_rows_for_tabular_intent() -> None:
    context = [
        {
            "is_tabular": True,
            "text": "name | quarter | value\nalpha | q1 | 10",
        }
    ]

    answer = generate_answer("alpha q1", context, tabular_intent=True)
    assert "cannot provide a row-grounded tabular answer" in answer.lower()


def test_generate_answer_uses_matched_rows_for_tabular_intent() -> None:
    context = [
        {
            "is_tabular": True,
            "matched_rows": [
                {"row_text": "alpha | q1 | 10", "matched_terms": ["alpha", "q1"]},
                {"row_text": "beta | q2 | 20", "matched_terms": ["q2"]},
            ],
        }
    ]

    answer = generate_answer("alpha q1", context, tabular_intent=True)
    assert "alpha | q1 | 10" in answer
