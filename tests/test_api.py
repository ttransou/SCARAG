from fastapi.testclient import TestClient

from api_server import app


def test_health_endpoint() -> None:
    client = TestClient(app)
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["contract_version"] == "1.0"


def test_chat_endpoint_handles_empty_query() -> None:
    client = TestClient(app)
    response = client.post("/api/chat", json={"query": "   "})
    assert response.status_code == 200
    body = response.json()
    assert body["contract_version"] == "1.0"
    assert body["answer"] == "Please provide a query."
    assert body["confidence"] == "abstain"
    assert body["message"]["citations_summary"]["total_count"] == 0


def test_chat_endpoint_returns_contract_fields() -> None:
    client = TestClient(app)
    response = client.post("/api/chat", json={"query": "policy"})
    assert response.status_code == 200

    body = response.json()
    assert body["contract_version"] == "1.0"
    assert "message" in body
    assert "text" in body["message"]
    assert "citations_summary" in body["message"]
    assert "tabular_trace" in body["message"]
    assert "provenance_validation" in body["message"]
    assert "generation" in body["message"]
    assert isinstance(body["message"]["generation"].get("abstained"), bool)
    assert isinstance(body["message"]["provenance_validation"].get("complete"), bool)
    assert "citations" in body
    assert "collapsed_citations" in body
    assert "answer" in body
    assert "confidence" in body
    assert body["confidence"] in {"high", "low", "abstain"}
