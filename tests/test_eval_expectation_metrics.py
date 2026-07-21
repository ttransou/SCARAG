from __future__ import annotations

import json
from pathlib import Path

from scripts.run_eval import (
    _read_jsonl,
    _correctness_proxy,
    _confidence_matches,
    _excluded_sources_respected,
    _faithfulness_proxy,
    _tabular_outcome_matches,
    _tabular_terms_matched,
    main as run_eval_main,
)


def test_confidence_matches_expectation() -> None:
    present, matched = _confidence_matches({"expected_confidence": "high"}, "high")
    assert present is True
    assert matched is True


def test_excluded_sources_respected_detects_violations() -> None:
    retrieved = [{"source": "data/retired_policy.md"}]
    present, compliant = _excluded_sources_respected(retrieved, {"excluded_sources": ["retired"]})
    assert present is True
    assert compliant is False


def test_tabular_terms_matched_detects_expected_terms() -> None:
    grounded_chunks = [{"matched_terms": ["alpha", "q1"]}]
    present, matched = _tabular_terms_matched(grounded_chunks, {"expected_tabular_terms": ["alpha"]})
    assert present is True
    assert matched is True


def test_tabular_outcome_matches_grounded_answer_expectation() -> None:
    grounded_chunks = [{"tabular_grounded": True, "matched_terms": ["alpha"]}]
    present, expected, matched = _tabular_outcome_matches(
        {"expected_tabular_outcome": "answer"},
        grounded_chunks,
        "alpha | q1 | 10",
    )

    assert present is True
    assert expected == "answer"
    assert matched is True


def test_tabular_outcome_matches_abstention_expectation() -> None:
    present, expected, matched = _tabular_outcome_matches(
        {"expected_tabular_outcome": "abstain"},
        [],
        "I cannot provide a row-grounded tabular answer because no matching table rows were retrieved.",
    )

    assert present is True
    assert expected == "abstain"
    assert matched is True


def test_faithfulness_proxy_scores_supported_answer_terms() -> None:
    present, score = _faithfulness_proxy(
        "Vacation policy requires manager approval for leave.",
        [{"text": "The vacation policy requires manager approval for leave over five days."}],
    )

    assert present is True
    assert score == 1.0


def test_read_jsonl_reports_malformed_rows_and_keeps_valid_rows(tmp_path: Path) -> None:
    dataset_path = tmp_path / "dataset.jsonl"
    dataset_path.write_text(
        "\n".join(
            [
                "{\"id\": \"ok-1\", \"query\": \"What is policy A?\"}",
                "not-json",
                "[\"wrong-shape\"]",
                "{\"id\": \"missing-query\", \"expected_sources\": [\"x\"]}",
                "{\"id\": \"bad-type\", \"query\": \"x\", \"expected_sources\": 123}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    rows, summary = _read_jsonl(dataset_path)

    assert len(rows) == 2
    assert rows[1]["expected_sources"] == []
    assert summary["total_nonempty_lines"] == 5
    assert summary["valid_rows"] == 2
    assert summary["invalid_rows"] == 3
    assert summary["parse_errors"] == 1
    assert any(issue["code"] == "invalid_json" for issue in summary["issues"])
    assert any(issue["code"] == "missing_query" for issue in summary["issues"])


def test_correctness_proxy_scores_expected_answer_terms_and_phrases() -> None:
    sample = {
        "expected_answer_terms": ["manager", "approval"],
        "expected_answer_contains": ["leave over five days"],
    }

    present, score = _correctness_proxy(
        sample,
        "Vacation policy requires manager approval for leave over five days.",
    )

    assert present is True
    assert score == 1.0


def test_offline_eval_writes_json_and_markdown_reports(tmp_path: Path, monkeypatch) -> None:
    data_dir = tmp_path / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "sample_policy.txt").write_text(
        "Vacation policy requires manager approval for leave over five days.\n",
        encoding="utf-8",
    )

    dataset_path = tmp_path / "dataset.jsonl"
    dataset_path.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "id": "sample-1",
                        "query": "What does the vacation policy require?",
                        "expected_sources": ["sample_policy.txt"],
                        "expected_confidence": "high",
                        "expected_answer_terms": ["manager", "approval"],
                        "expected_answer_contains": ["leave over five days"],
                    }
                ),
                "{invalid-json-row}",
                json.dumps({"id": "missing-query", "expected_sources": ["sample_policy.txt"]}),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    thesaurus_path = tmp_path / "synonyms.json"
    thesaurus_path.write_text(json.dumps({"terms": {}, "intent_groups": {}}) + "\n", encoding="utf-8")

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        "sys.argv",
        [
            "run_eval.py",
            "--data",
            str(data_dir),
            "--dataset",
            str(dataset_path),
            "--thesaurus",
            str(thesaurus_path),
        ],
    )

    run_eval_main()

    reports_dir = tmp_path / "eval" / "reports"
    json_reports = sorted(reports_dir.glob("offline_eval_*.json"))
    md_reports = sorted(reports_dir.glob("offline_eval_*.md"))

    assert len(json_reports) == 1
    assert len(md_reports) == 1

    report = json.loads(json_reports[0].read_text(encoding="utf-8"))
    assert report["sample_count"] == 1
    assert report["datasets"] == [str(dataset_path)]
    assert "hit_rate_at_k" in report["metrics"]
    assert "provenance_completeness" in report["metrics"]
    assert "faithfulness_proxy" in report["metrics"]
    assert "correctness_proxy" in report["metrics"]
    assert report["metrics"]["faithfulness_proxy"] == 1.0
    assert report["metrics"]["correctness_proxy"] == 1.0
    assert "dataset_sanity" in report
    assert report["dataset_sanity"]["total_nonempty_rows"] == 3
    assert report["dataset_sanity"]["valid_rows"] == 1
    assert report["dataset_sanity"]["invalid_rows"] == 2
    assert report["dataset_sanity"]["parse_errors"] == 1
    assert len(report["dataset_sanity"]["issue_preview"]) >= 1

    markdown = md_reports[0].read_text(encoding="utf-8")
    assert "# SCARAG Offline Evaluation" in markdown
    assert "| hit_rate_at_k |" in markdown
    assert "| faithfulness_proxy |" in markdown
    assert "| correctness_proxy |" in markdown
    assert "## Dataset Sanity" in markdown
    assert "### Malformed Row Preview" in markdown
