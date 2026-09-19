import pytest
from fastapi.testclient import TestClient

from app import crew_room
from app.config import settings
from app.main import app
from app.providers import vonage

client = TestClient(app)


class FakeVonage:
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


def room_id(link: str) -> str:
    return link.rsplit("/crew/", 1)[1]


def test_the_command_post_opens_one_room_with_a_link_for_the_crews(fake: FakeVonage) -> None:
    first = client.post("/api/crew-room").json()
    again = client.post("/api/crew-room").json()

    assert "/crew/" in first["link"]
    assert again["link"] == first["link"]
    assert fake.sessions == ["session-1"]
    assert first["access"]["session_id"] == "session-1"


def test_every_crew_joins_the_same_room_with_the_link(fake: FakeVonage) -> None:
    link = client.post("/api/crew-room").json()["link"]

    crews = [client.get(f"/api/crew-room/{room_id(link)}") for _ in range(2)]

    assert [c.status_code for c in crews] == [200, 200]
    assert {c.json()["session_id"] for c in crews} == {"session-1"}
    assert client.get("/api/crew-room/nope").status_code == 404


def test_the_room_has_spanish_captions(fake: FakeVonage) -> None:
    client.post("/api/crew-room")

    assert fake.captions == [("session-1", "es-ES")]


def test_the_link_is_texted_to_the_crew_phone(fake: FakeVonage, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(crew_room, "settings", type(settings)(**{**settings.__dict__, "crew_phone": "+34000000099"}))

    link = client.post("/api/crew-room").json()["link"]

    assert [(to, link in text) for to, text in fake.texts] == [("+34000000099", True)]


def test_a_reset_closes_the_room(fake: FakeVonage) -> None:
    link = client.post("/api/crew-room").json()["link"]

    client.post("/api/reset")

    assert client.get(f"/api/crew-room/{room_id(link)}").status_code == 404
