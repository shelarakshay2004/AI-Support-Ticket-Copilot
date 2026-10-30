import pytest
from fastapi.testclient import TestClient

import backend.database as database
import backend.main as main
from backend.schemas import TicketAnalysis


@pytest.fixture
def client(tmp_path, monkeypatch):
    # Give each test its own temporary SQLite database.
    monkeypatch.setattr(database, "DATA_DIR", tmp_path)
    monkeypatch.setattr(database, "DB_PATH", tmp_path / "tickets.db")

    # Mock Gemini so tests do not make real API calls.
    def fake_analyze_ticket(ticket):
        return TicketAnalysis(
            category="account",
            priority="medium",
            summary="Customer cannot log in after resetting the password.",
            suggested_reply=(
                "Please share the exact error message you see when signing in."
            ),
            should_escalate=True,
            escalation_reason=(
                "Persistent login problems require human review."
            ),
        )

    monkeypatch.setattr(main, "analyze_ticket", fake_analyze_ticket)

    with TestClient(main.app) as test_client:
        yield test_client


def sample_ticket():
    return {
        "subject": "Password reset problem",
        "message": (
            "I reset my password twice, but I still cannot log into my account."
        ),
        "category_hint": "account",
    }


def test_health_endpoint(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_create_ticket_and_save_to_database(client):
    response = client.post("/tickets", json=sample_ticket())

    assert response.status_code == 200

    body = response.json()
    assert body["ticket_id"]
    assert body["status"] == "escalated"
    assert body["analysis"]["category"] == "account"

    history = client.get("/tickets")

    assert history.status_code == 200
    assert history.json()["count"] == 1
    assert history.json()["tickets"][0]["ticket_id"] == body["ticket_id"]


def test_update_ticket_status(client):
    created = client.post("/tickets", json=sample_ticket())
    ticket_id = created.json()["ticket_id"]

    response = client.patch(
        f"/tickets/{ticket_id}/status",
        json={"status": "resolved"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "resolved"

    history = client.get("/tickets").json()
    assert history["tickets"][0]["status"] == "resolved"


def test_missing_ticket_returns_404(client):
    response = client.patch(
        "/tickets/nonexistent-ticket/status",
        json={"status": "resolved"},
    )

    assert response.status_code == 404


def test_invalid_ticket_input_returns_422(client):
    response = client.post(
        "/tickets",
        json={
            "subject": "Hi",
            "message": "Bad",
            "category_hint": "account",
        },
    )

    assert response.status_code == 422