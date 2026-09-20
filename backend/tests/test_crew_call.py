"""A resident who cannot leave becomes a phone call to the crew, not just a line on a dashboard.

The call is placed by the crew-caller agent (SLNG_CREW_AGENT_ID), which reads the rescue queue, the
plan and each route with its own tools, so it says what is true at the moment it rings.
"""

import pytest
from fastapi.testclient import TestClient

from app import main
from app.config import settings
from app.main import app
from app.providers import voice

client = TestClient(app)


@pytest.fixture(autouse=True)
def fresh():
    client.post("/api/reset")


@pytest.fixture
def dialled(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    calls: list[str] = []
    monkeypatch.setattr(voice, "crew_calls_configured", lambda: True)
    monkeypatch.setattr(voice, "call_crew", lambda phone: calls.append(phone) or "call-1")
    monkeypatch.setattr(main, "settings", type(settings)(**{**settings.__dict__, "crew_phone": "+34000000099"}))
    return calls


def rescue(neighbor_id: str) -> None:
    client.post("/tools/report_status", json={"neighbor_id": neighbor_id, "status": "needs_rescue", "people": 2})


def first_id() -> str:
    return client.get("/api/neighbors").json()[0]["id"]


def test_a_new_rescue_rings_the_crew(dialled: list[str]) -> None:
    rescue(first_id())

    assert dialled == ["+34000000099"]


def test_the_same_rescue_rings_once(dialled: list[str]) -> None:
    rescue(first_id())
    rescue(first_id())

    assert len(dialled) == 1


def test_nothing_is_dialled_until_crew_calls_are_turned_on(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(voice, "crew_calls_configured", lambda: False)
    monkeypatch.setattr(voice, "call_crew", lambda phone: pytest.fail("crew calls are off"))

    rescue(first_id())

    assert client.get("/api/alerts").json(), "the alert still reaches the dashboard"


def test_a_failed_call_never_breaks_the_agent_s_tool(dialled: list[str], monkeypatch: pytest.MonkeyPatch) -> None:
    def refused(_phone: str) -> str:
        raise voice.VoiceUnavailable("SLNG said no")

    monkeypatch.setattr(voice, "call_crew", refused)

    response = client.post("/tools/report_status", json={"neighbor_id": first_id(), "status": "needs_rescue"})

    assert response.status_code == 200
