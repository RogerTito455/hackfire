import httpx
import pytest
from fastapi.testclient import TestClient

from app import main
from app.config import settings
from app.main import app
from app.providers import sms

client = TestClient(app)


@pytest.fixture(autouse=True)
def fresh():
    client.post("/api/reset")


@pytest.fixture
def twilio(monkeypatch: pytest.MonkeyPatch):
    sent: list[tuple[str, str]] = []
    monkeypatch.setattr(sms, "configured", lambda: True)
    monkeypatch.setattr(main, "settings", type(settings)(**{**settings.__dict__, "crew_phone": "+34000000099"}))
    monkeypatch.setattr(sms, "send", lambda to, body: sent.append((to, body)) or "SM123")
    return sent


def rescue(neighbor_id: str) -> None:
    client.post("/tools/report_status", json={"neighbor_id": neighbor_id, "status": "needs_rescue", "people": 2})


def first_id() -> str:
    return client.get("/api/neighbors").json()[0]["id"]


def test_a_new_rescue_is_texted_to_the_crew(twilio) -> None:
    rescue(first_id())
    alert = client.get("/api/alerts").json()[0]
    assert twilio == [("+34000000099", alert["message"])]
    assert alert["sent_by_sms"] is True


def test_the_same_rescue_is_texted_once(twilio) -> None:
    rescue(first_id())
    rescue(first_id())
    assert len(twilio) == 1


def test_without_twilio_nothing_is_sent_and_the_alert_stays_on_the_dashboard(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sms, "configured", lambda: False)
    monkeypatch.setattr(sms, "send", lambda *_: pytest.fail("must not send"))
    rescue(first_id())
    assert client.get("/api/alerts").json()[0]["sent_by_sms"] is False


def test_a_twilio_failure_never_breaks_the_tool(twilio, monkeypatch: pytest.MonkeyPatch) -> None:
    def down(*_):
        raise httpx.ConnectTimeout("timed out")

    monkeypatch.setattr(sms, "send", down)
    response = client.post("/tools/report_status", json={"neighbor_id": first_id(), "status": "needs_rescue"})
    assert response.status_code == 200
    assert client.get("/api/alerts").json()[0]["sent_by_sms"] is False


def test_twilio_gets_the_right_request(monkeypatch: pytest.MonkeyPatch) -> None:
    seen = {}

    def fake_post(url, auth, data, timeout):
        seen.update(url=url, auth=auth, data=data)
        return httpx.Response(201, json={"sid": "SM1"}, request=httpx.Request("POST", url))

    monkeypatch.setattr(sms.httpx, "post", fake_post)
    monkeypatch.setattr(
        sms,
        "settings",
        type(settings)(
            **{**settings.__dict__, "twilio_account_sid": "AC1", "twilio_auth_token": "tok", "twilio_from_number": "+100"}
        ),
    )
    assert sms.send("+34000000099", "Rescue needed") == "SM1"
    assert seen["url"] == "https://api.twilio.com/2010-04-01/Accounts/AC1/Messages.json"
    assert seen["auth"] == ("AC1", "tok")
    assert seen["data"] == {"To": "+34000000099", "From": "+100", "Body": "Rescue needed"}
