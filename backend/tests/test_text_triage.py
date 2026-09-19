import json

import pytest
from fastapi.testclient import TestClient

from app import text_triage
from app.main import app
from app.providers import llm
from app.state import state

client = TestClient(app)


@pytest.fixture(autouse=True)
def fresh():
    client.post("/api/reset")


@pytest.fixture
def fake_llm(monkeypatch: pytest.MonkeyPatch):
    sent: list[dict] = []

    def answer(_client, messages, **params):
        sent.append({"messages": messages, **params})
        return json.dumps(
            {"status": "needs_rescue", "people": 2, "mobility": "mother cannot walk", "observation": "smoke to the west"}
        )

    monkeypatch.setattr(text_triage, "available", lambda: True)
    monkeypatch.setattr(llm, "chat", answer)
    return sent


def resident() -> dict:
    return client.get("/api/neighbors").json()[0]


def test_a_typed_answer_is_triaged_like_a_call(fake_llm) -> None:
    neighbor = resident()
    body = client.post(
        "/api/triage/text", json={"neighbor_id": neighbor["id"], "text": "Mi madre no puede andar y vemos humo al oeste"}
    ).json()

    assert body["classification"]["status"] == "needs_rescue"
    assert body["neighbor"]["status"] == "needs_rescue"
    assert body["neighbor"]["people"] == 2
    # Same path as a call: rescue queue and crew alert.
    assert [r["neighbor"]["id"] for r in client.get("/api/rescues").json()] == [neighbor["id"]]
    assert client.get("/api/alerts").json()[0]["neighbor_id"] == neighbor["id"]


def test_the_llm_gets_the_rules_and_a_strict_schema(fake_llm) -> None:
    client.post("/api/triage/text", json={"neighbor_id": resident()["id"], "text": "No tenemos coche"})
    request = fake_llm[0]
    assert request["messages"][0]["content"] == text_triage.SYSTEM_PROMPT
    assert request["messages"][1]["content"] == "No tenemos coche"
    assert request["response_format"]["type"] == "json_schema"
    assert request["response_format"]["json_schema"]["schema"]["properties"]["status"]["enum"] == [
        "evacuating",
        "no_answer",
        "needs_rescue",
    ]
    assert request["temperature"] == 0


def test_without_an_llm_the_dashboard_is_told_to_use_the_buttons(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(text_triage, "available", lambda: False)
    response = client.post("/api/triage/text", json={"neighbor_id": resident()["id"], "text": "hola"})
    assert response.status_code == 503
    assert client.get("/api/neighbors").json()[0]["status"] == "pending"


def test_a_garbled_llm_answer_is_a_503_not_a_wrong_pin(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(text_triage, "available", lambda: True)
    monkeypatch.setattr(llm, "chat", lambda *_args, **_kw: '{"status": "on fire"}')
    response = client.post("/api/triage/text", json={"neighbor_id": resident()["id"], "text": "hola"})
    assert response.status_code == 503
    assert client.get("/api/neighbors").json()[0]["status"] == "pending"


def test_unknown_resident_is_a_404(fake_llm) -> None:
    assert client.post("/api/triage/text", json={"neighbor_id": "nobody", "text": "hola"}).status_code == 404


def test_availability_is_reported() -> None:
    assert isinstance(client.get("/api/triage/text").json()["available"], bool)


def test_reset_forgets_the_replay_moment() -> None:
    client.post("/api/replay/time", json={"at": "2026-07-23T12:00:00Z"})
    assert state.replay_time is not None
    client.post("/api/reset")
    assert state.replay_time is None


def test_typed_answers_use_the_voice_agents_own_rules() -> None:
    # If the "Cómo clasificar" section of voice/resident/instructions.md is renamed, this fails
    # instead of silently falling back to a second copy of the rules.
    assert text_triage._agent_rules() != text_triage.FALLBACK_RULES
    assert text_triage._agent_rules() in text_triage.SYSTEM_PROMPT
