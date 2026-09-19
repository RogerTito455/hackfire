"""A browser call that ends with nothing recorded leaves the resident flagged for a follow-up call."""

import pytest
from fastapi.testclient import TestClient

from app import main
from app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def no_grace(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(main, "CALL_END_GRACE_S", 0)
    client.post("/api/reset")
    yield
    client.post("/api/reset")


def status_of(neighbor_id: str) -> dict:
    return next(n for n in client.get("/api/neighbors").json() if n["id"] == neighbor_id)


def test_a_call_that_ended_without_a_report_becomes_no_answer_with_a_note() -> None:
    neighbor = client.get("/api/neighbors").json()[0]
    assert client.post(f"/api/neighbors/{neighbor['id']}/call-ended").status_code == 200
    after = status_of(neighbor["id"])
    assert after["status"] == "no_answer"
    assert after["observation"] == "The call ended without a recorded answer: call again."


def test_the_note_follows_the_dashboard_language() -> None:
    neighbor = client.get("/api/neighbors").json()[0]
    client.post(f"/api/neighbors/{neighbor['id']}/call-ended", headers={"Accept-Language": "es"})
    assert status_of(neighbor["id"])["observation"].startswith("La llamada terminó sin respuesta registrada")


def test_what_the_agent_recorded_is_never_overwritten() -> None:
    neighbor = client.get("/api/neighbors").json()[0]
    client.post("/tools/report_status", json={"neighbor_id": neighbor["id"], "status": "needs_rescue", "people": 2})
    client.post(f"/api/neighbors/{neighbor['id']}/call-ended")
    assert status_of(neighbor["id"])["status"] == "needs_rescue"


def test_an_unknown_resident_is_a_404() -> None:
    assert client.post("/api/neighbors/nobody/call-ended").status_code == 404
