from __future__ import annotations

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
    assert isinstance(body.get("message"), dict)
    assert isinstance(body.get("citations"), list)
    assert isinstance(body.get("collapsed_citations"), list)
    assert isinstance(body.get("answer"), str)
    assert isinstance(body.get("confidence"), str)

    summary = body["message"]["citations_summary"]
    assert isinstance(summary.get("count"), int)
    assert isinstance(summary.get("total_count"), int)
    assert isinstance(summary.get("hidden_count"), int)
    assert summary["total_count"] == len(body["citations"]) + len(body["collapsed_citations"])
    assert summary["count"] == len(body["citations"])
    assert summary["hidden_count"] == len(body["collapsed_citations"])


def test_chat_collapses_low_score_citation_when_hidden_set_is_empty(monkeypatch) -> None:
    monkeypatch.setattr(
        api_server,
        "_CHUNK_CACHE",
        [
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
                "text": "alpha",
                "doc_type": "unknown",
                "is_tabular": False,
            },
        ],
    )
    monkeypatch.setattr(api_server, "_THESAURUS", {"terms": {}, "intent_groups": {}})

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
