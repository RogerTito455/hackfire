import pytest
from fastapi.testclient import TestClient

from app import rescue_video
from app.main import app
from app.providers import vonage
from app.state import state

client = TestClient(app)


class FakeVonage:
    """Vonage Video and SMS, as the rescue video sees them through providers/vonage.py."""

    def __init__(self) -> None:
        self.sessions: list[str] = []
        self.tokens: list[tuple[str, str]] = []
        self.captions: list[tuple[str, str]] = []
        self.texts: list[tuple[str, str]] = []

    def create_session(self) -> str:
        self.sessions.append(f"session-{len(self.sessions) + 1}")
        return self.sessions[-1]

    def client_token(self, session_id: str, role: str, ttl_s: int) -> str:
        self.tokens.append((session_id, role))
        return f"token-{role}-{session_id}"

    def start_captions(self, session_id: str, language: str) -> None:
        self.captions.append((session_id, language))

    def send_sms(self, to_e164: str, text: str) -> None:
        self.texts.append((to_e164, text))


@pytest.fixture(autouse=True)
def fresh():
    client.post("/api/reset")


@pytest.fixture
def fake(monkeypatch: pytest.MonkeyPatch) -> FakeVonage:
    line = FakeVonage()
    monkeypatch.setattr(vonage, "video_configured", lambda: True)
    monkeypatch.setattr(vonage, "sms_configured", lambda: True)
    for name in ("create_session", "client_token", "start_captions", "send_sms"):
        monkeypatch.setattr(vonage, name, getattr(line, name))
    return line


def needs_rescue(neighbor_id: str) -> None:
    client.post("/tools/report_status", json={"neighbor_id": neighbor_id, "status": "needs_rescue", "people": 2})


def test_video_is_only_for_a_resident_who_needs_rescue(fake: FakeVonage) -> None:
    assert client.post("/api/rescues/n01/video").status_code == 409
    assert client.post("/api/rescues/nobody/video").status_code == 404
    assert fake.sessions == [] and fake.texts == []

    needs_rescue("n01")

    assert client.post("/api/rescues/n01/video").status_code == 200


def test_the_link_is_texted_to_the_residents_registry_phone_and_never_returned(fake: FakeVonage) -> None:
    needs_rescue("n01")

    response = client.post("/api/rescues/n01/video")

    link = response.json()["link"]
    assert response.json()["sms_sent"] is True
    assert "/v/" in link
    [(to, text)] = fake.texts
    assert to == state.get("n01").phone  # the registry's number; the API never shows it
    assert link in text
    assert to not in response.text
    assert to.lstrip("+") not in client.get("/api/neighbors").text


def link_id_for(neighbor_id: str) -> str:
    needs_rescue(neighbor_id)
    return client.post(f"/api/rescues/{neighbor_id}/video").json()["link"].rsplit("/v/", 1)[1]


def test_the_link_opens_the_camera_once(fake: FakeVonage) -> None:
    link_id = link_id_for("n01")

    first = client.get(f"/api/video/{link_id}")

    assert first.status_code == 200
    assert first.json()["session_id"] == fake.sessions[0]
    assert first.json()["token"] == f"token-publisher-{fake.sessions[0]}"
    assert client.get(f"/api/video/{link_id}").status_code == 410
    assert client.get("/api/video/not-a-link").status_code == 404


def test_the_coordinator_watches_only_once_the_resident_is_on_camera(fake: FakeVonage) -> None:
    assert client.get("/api/rescues/n01/video").status_code == 404
    link_id = link_id_for("n01")

    waiting = client.get("/api/rescues/n01/video").json()
    client.get(f"/api/video/{link_id}")
    watching = client.get("/api/rescues/n01/video").json()

    assert waiting == {"neighbor_id": "n01", "joined": False, "access": None}
    assert watching["joined"] is True
    assert watching["access"]["session_id"] == fake.sessions[0]
    assert watching["access"]["token"] == f"token-subscriber-{fake.sessions[0]}"


def test_spanish_captions_start_when_the_resident_turns_on_the_camera(fake: FakeVonage) -> None:
    link_id = link_id_for("n01")
    assert fake.captions == []

    client.get(f"/api/video/{link_id}")

    assert fake.captions == [(fake.sessions[0], "es-ES")]


def test_a_reset_forgets_every_link_and_session(fake: FakeVonage) -> None:
    link_id = link_id_for("n01")

    client.post("/api/reset")

    assert client.get(f"/api/video/{link_id}").status_code == 404
    assert client.get("/api/rescues/n01/video").status_code == 404


def test_without_vonage_credentials_the_dashboard_hides_video_and_asking_fails_cleanly(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(vonage, "video_configured", lambda: False)
    monkeypatch.setattr(vonage, "sms_configured", lambda: False)
    needs_rescue("n01")

    assert client.get("/api/video").json() == {"video": False, "sms": False}
    assert client.post("/api/rescues/n01/video").status_code == 503
