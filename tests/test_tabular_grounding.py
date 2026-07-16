from __future__ import annotations

from scarag.generation.answerer import generate_answer_result
from scarag.pipeline import is_tabular_intent
from scarag.generation.answerer import generate_answer
from scarag.tabular_grounding import apply_tabular_grounding


def test_is_tabular_intent_detects_terms_from_thesaurus_group() -> None:
    thesaurus = {"intent_groups": {"tabular": ["table", "rows", "quarterly totals"]}}

    assert is_tabular_intent("show quarterly totals", thesaurus) is True
    assert is_tabular_intent("policy exception workflow", thesaurus) is False


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


def test_generate_answer_result_emits_abstention_reason_code() -> None:
    result = generate_answer_result("policy", [], tabular_intent=False)

    assert result.abstained is True
    assert result.reason_code == "no_supporting_evidence"
    assert result.cited_chunk_ids == []


def test_generate_answer_result_tracks_cited_chunk_ids_for_extractve_mode() -> None:
    context = [
        {"chunk_id": "policy:0", "text": "policy alpha"},
        {"chunk_id": "policy:1", "text": "policy beta"},
        {"chunk_id": "policy:2", "text": "policy gamma"},
        {"chunk_id": "policy:3", "text": "policy delta"},
    ]

    result = generate_answer_result("policy", context)

    assert result.abstained is False
    assert result.cited_chunk_ids == ["policy:0", "policy:1", "policy:2"]
    assert result.used_context_count == 3
