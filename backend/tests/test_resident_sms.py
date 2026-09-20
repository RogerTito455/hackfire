"""A resident who is leaving gets their way out by SMS: a link that drives the route we planned.

Sent only where it is turned on (HACKFIRE_RESIDENT_SMS), to anyone who answered: someone waiting
for a crew still has to be able to move if the fire arrives first.
"""

import pytest
from fastapi.testclient import TestClient

from app import main
from app.config import settings
from app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def fresh():
    client.post("/api/reset")


@pytest.fixture
def texted(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, str]]:
    sent: list[tuple[str, str]] = []
    monkeypatch.setattr(main.vonage, "sms_configured", lambda: True)
    monkeypatch.setattr(main.vonage, "send_sms", lambda to, text: sent.append((to, text)))
    monkeypatch.setattr(main, "settings", type(settings)(**{**settings.__dict__, "resident_sms": True}))
    return sent


def report(neighbor_id: str, status: str) -> None:
    client.post("/tools/report_status", json={"neighbor_id": neighbor_id, "status": status, "people": 2})


def first() -> dict:
    return client.get("/api/neighbors").json()[0]


def test_a_resident_who_is_leaving_gets_the_route_by_sms(texted: list[tuple[str, str]]) -> None:
    report(first()["id"], "evacuating")

    assert len(texted) == 1
    number, text = texted[0]
    assert number.startswith("+")
    assert "https://www.google.com/maps/dir/?api=1" in text


def test_a_resident_who_needs_rescue_gets_the_way_out_too(texted: list[tuple[str, str]]) -> None:
    """Help is coming, but the fire may get there first: they have to be able to move anyway."""
    report(first()["id"], "needs_rescue")

    assert len(texted) == 1
    assert "https://www.google.com/maps/dir/?api=1" in texted[0][1]


def test_a_resident_who_never_answered_is_not_texted(texted: list[tuple[str, str]]) -> None:
    report(first()["id"], "no_answer")

    assert texted == []


def test_nothing_is_texted_until_it_is_turned_on(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(main.vonage, "sms_configured", lambda: True)
    monkeypatch.setattr(main.vonage, "send_sms", lambda *_: pytest.fail("resident SMS is off"))

    report(first()["id"], "evacuating")
