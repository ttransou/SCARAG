from __future__ import annotations

from types import SimpleNamespace

from fastapi.testclient import TestClient

import api_server


def test_chat_contract_type_stability_and_counts(monkeypatch) -> None:
    monkeypatch.setattr(
        api_server,
        "_CHUNK_CACHE",
        [
            {
                "chunk_id": "doc1:0",
                "source": "data/policy-1.md",
                "text": "policy alpha beta",
                "doc_type": "policy",
                "is_tabular": False,
            },
            {
                "chunk_id": "doc2:0",
                "source": "data/policy-2.md",
                "text": "policy alpha details",
                "doc_type": "policy",
                "is_tabular": False,
            },
            {
                "chunk_id": "doc3:0",
                "source": "data/policy-3.md",
                "text": "policy guidance",
                "doc_type": "policy",
                "is_tabular": False,
            },
            {
                "chunk_id": "doc4:0",
                "source": "data/policy-4.md",
                "text": "policy controls",
                "doc_type": "policy",
                "is_tabular": False,
            },
        ],
    )
    monkeypatch.setattr(api_server, "_THESAURUS", {"terms": {}, "intent_groups": {}})

    client = TestClient(api_server.app)
    response = client.post("/api/chat", json={"query": "policy alpha"})
    assert response.status_code == 200

    body = response.json()
    assert body["contract_version"] == "1.0"
    assert isinstance(body.get("message"), dict)
    assert isinstance(body.get("citations"), list)
    assert isinstance(body.get("collapsed_citations"), list)
    assert isinstance(body.get("answer"), str)
    assert isinstance(body.get("confidence"), str)
    assert isinstance(body["message"].get("generation"), dict)
    assert isinstance(body["message"]["generation"].get("abstained"), bool)
    assert isinstance(body["message"]["generation"].get("cited_chunk_ids"), list)

    summary = body["message"]["citations_summary"]
    assert isinstance(summary.get("count"), int)
    assert isinstance(summary.get("total_count"), int)
    assert isinstance(summary.get("hidden_count"), int)
    assert summary["total_count"] == len(body["citations"]) + len(body["collapsed_citations"])
    assert summary["count"] == len(body["citations"])
    assert summary["hidden_count"] == len(body["collapsed_citations"])


def test_chat_contract_version_is_stable_string(monkeypatch) -> None:
    monkeypatch.setattr(
        api_server,
        "_CHUNK_CACHE",
        [
            {
                "chunk_id": "doc1:0",
                "source": "data/policy-1.md",
                "text": "policy alpha beta",
                "doc_type": "policy",
                "is_tabular": False,
            }
        ],
    )
    monkeypatch.setattr(api_server, "_THESAURUS", {"terms": {}, "intent_groups": {}})

    client = TestClient(api_server.app)
    response = client.post("/api/chat", json={"query": "policy alpha"})
    assert response.status_code == 200

    body = response.json()
    assert isinstance(body.get("contract_version"), str)
    assert body["contract_version"] == "1.0"


def test_chat_collapses_low_score_citation_when_hidden_set_is_empty(monkeypatch) -> None:
    chunks = [
        {
            "chunk_id": "top:0",
            "source": "data/top.md",
            "text": "alpha beta gamma",
            "doc_type": "policy",
            "is_tabular": False,
        },
        {
            "chunk_id": "low:0",
            "source": "data/low.md",
            "text": "alpha beta",
            "doc_type": "unknown",
            "is_tabular": False,
        },
    ]
    monkeypatch.setattr(api_server, "_CHUNK_CACHE", chunks)
    monkeypatch.setattr(api_server, "_THESAURUS", {"terms": {}, "intent_groups": {}})
    monkeypatch.setattr(
        api_server,
        "retrieve_chunks",
        lambda *args, **kwargs: [
            {**chunks[0], "score": 0.95},
            {**chunks[1], "score": 0.2},
        ],
    )

    client = TestClient(api_server.app)
    response = client.post("/api/chat", json={"query": "alpha beta gamma"})
    assert response.status_code == 200

    body = response.json()
    summary = body["message"]["citations_summary"]

    assert summary["total_count"] == 2
    assert summary["count"] == 1
    assert summary["hidden_count"] == 1
    assert len(body["citations"]) == 1
    assert len(body["collapsed_citations"]) == 1
    assert body["collapsed_citations"][0]["id"] == "low:0"


def test_chat_confidence_is_restricted_to_contract_labels(monkeypatch) -> None:
    monkeypatch.setattr(
        api_server,
        "_CHUNK_CACHE",
        [
            {
                "chunk_id": "doc1:0",
                "source": "data/policy-1.md",
                "text": "policy alpha beta",
                "doc_type": "policy",
                "is_tabular": False,
            }
        ],
    )
    monkeypatch.setattr(api_server, "_THESAURUS", {"terms": {}, "intent_groups": {}})
    monkeypatch.setattr(
        api_server,
        "resolve_confidence",
        lambda *args, **kwargs: SimpleNamespace(label="medium", score=0.6, reason="synthetic"),
    )

    client = TestClient(api_server.app)
    response = client.post("/api/chat", json={"query": "policy alpha"})
    assert response.status_code == 200

    body = response.json()
    assert body["confidence"] == "abstain"


def test_chat_filters_incomplete_provenance_and_reports_enforcement(monkeypatch) -> None:
    monkeypatch.setattr(
        api_server,
        "_CHUNK_CACHE",
        [
            {
                "chunk_id": "",
                "source": "",
                "text": "policy alpha invalid",
                "doc_type": "policy",
                "is_tabular": False,
            },
            {
                "chunk_id": "doc-good:0",
                "source": "data/policy-good.md",
                "text": "policy alpha valid",
                "doc_type": "policy",
                "is_tabular": False,
            },
        ],
    )
    monkeypatch.setattr(api_server, "_THESAURUS", {"terms": {}, "intent_groups": {}})

    client = TestClient(api_server.app)
    response = client.post("/api/chat", json={"query": "policy alpha"})
    assert response.status_code == 200

    body = response.json()
    summary = body["message"]["citations_summary"]
    enforcement = body["message"]["provenance_validation"]["enforcement"]

    assert summary["total_count"] == 1
    assert len(body["citations"]) + len(body["collapsed_citations"]) == 1
    assert enforcement["source_chunks"]["dropped"] >= 1
    assert enforcement["source_chunks"]["missing_by_field"]["source"] >= 1
    assert enforcement["source_chunks"]["missing_by_field"]["chunk_id"] >= 1


def test_chat_drops_duplicate_and_untraceable_citations_from_visible_sets(monkeypatch) -> None:
    monkeypatch.setattr(
        api_server,
        "_CHUNK_CACHE",
        [
            {
                "chunk_id": "dup:0",
                "source": "data/policy-dup.md",
                "text": "policy alpha duplicate snippet with enough detail",
                "doc_type": "policy",
                "is_tabular": False,
            },
            {
                "chunk_id": "dup:0",
                "source": "data/policy-dup.md",
                "text": "policy alpha duplicate snippet with enough detail",
                "doc_type": "policy",
                "is_tabular": False,
            },
            {
                "chunk_id": "short:0",
                "source": "data/policy-short.md",
                "text": "alpha",
                "doc_type": "policy",
                "is_tabular": False,
            },
        ],
    )
    monkeypatch.setattr(api_server, "_THESAURUS", {"terms": {}, "intent_groups": {}})

    client = TestClient(api_server.app)
    response = client.post("/api/chat", json={"query": "policy alpha"})
    assert response.status_code == 200

    body = response.json()
    enforcement = body["message"]["provenance_validation"]["enforcement"]["citations"]

    assert len(body["citations"]) == 1
    assert len(body["collapsed_citations"]) == 0
    assert body["citations"][0]["id"] == "dup:0"
    assert body["message"]["generation"]["cited_chunk_ids"] == ["dup:0"]
    assert enforcement["quality"]["dropped_by_reason"]["duplicate_policy"] == 0
    assert enforcement["quality"]["dropped_by_reason"]["snippet_adequacy"] == 0


def test_chat_abstains_for_tabular_intent_without_tabular_evidence(monkeypatch) -> None:
    monkeypatch.setattr(
        api_server,
        "_CHUNK_CACHE",
        [
            {
                "chunk_id": "policy:0",
                "source": "data/policy.md",
                "text": "policy guidance for quarterly review cycles",
                "doc_type": "policy",
                "is_tabular": False,
            }
        ],
    )
    monkeypatch.setattr(api_server, "_THESAURUS", {"terms": {}, "intent_groups": {"tabular": ["quarterly", "rows", "table"]}})

    client = TestClient(api_server.app)
    response = client.post("/api/chat", json={"query": "show quarterly rows"})
    assert response.status_code == 200

    body = response.json()

    assert body["confidence"] == "abstain"
    assert "row-grounded tabular answer" in body["answer"].lower()
    assert body["message"]["tabular_trace"]["tabular_intent"] is True
    assert body["message"]["tabular_trace"]["reason"] == "no_matched_rows"
    assert body["message"]["citations_summary"]["total_count"] == 0
    assert body["message"]["generation"]["abstained"] is True
    assert body["message"]["generation"]["reason_code"] == "tabular_row_evidence_missing"


def test_chat_citations_follow_generation_used_chunks(monkeypatch) -> None:
    monkeypatch.setattr(
        api_server,
        "_CHUNK_CACHE",
        [
            {
                "chunk_id": "doc1:0",
                "source": "data/policy-1.md",
                "text": "policy alpha beta",
                "doc_type": "policy",
                "is_tabular": False,
            },
            {
                "chunk_id": "doc2:0",
                "source": "data/policy-2.md",
                "text": "policy alpha details",
                "doc_type": "policy",
                "is_tabular": False,
            },
            {
                "chunk_id": "doc3:0",
                "source": "data/policy-3.md",
                "text": "policy guidance",
                "doc_type": "policy",
                "is_tabular": False,
            },
            {
                "chunk_id": "doc4:0",
                "source": "data/policy-4.md",
                "text": "policy controls",
                "doc_type": "policy",
                "is_tabular": False,
            },
        ],
    )
    monkeypatch.setattr(api_server, "_THESAURUS", {"terms": {}, "intent_groups": {}})

    client = TestClient(api_server.app)
    response = client.post("/api/chat", json={"query": "policy alpha"})
    assert response.status_code == 200

    body = response.json()

    assert body["message"]["generation"]["cited_chunk_ids"] == ["doc1:0", "doc2:0", "doc3:0"]
    assert body["message"]["citations_summary"]["total_count"] == 3
    assert [citation["id"] for citation in body["citations"]] == ["doc1:0", "doc2:0", "doc3:0"]
