import pytest
from fastapi.testclient import TestClient

from app import campaign
from app.main import app
from app.providers import voice

client = TestClient(app)


class FakeLine:
    """SLNG's outbound calls, as the campaign sees them through providers/voice.py."""

    def __init__(self) -> None:
        self.dialled: list[tuple[str, dict[str, str]]] = []
        # What residents tell the agent before the call ends, by neighbor id.
        self.answers: dict[str, str] = {}
        # Residents whose call SLNG refuses to place.
        self.refused: set[str] = set()
        # Residents whose call status SLNG fails to return once.
        self.status_errors: set[str] = set()

    def dial(self, phone: str, arguments: dict[str, str]) -> str:
        if arguments["neighbor_id"] in self.refused:
            raise voice.VoiceUnavailable("503 from SLNG")
        self.dialled.append((phone, arguments))
        return f"call-{arguments['neighbor_id']}"

    def ended(self, call_id: str) -> bool:
        neighbor_id = call_id.removeprefix("call-")
        if neighbor_id in self.status_errors:
            self.status_errors.remove(neighbor_id)
            raise voice.VoiceUnavailable("timeout")
        if neighbor_id in self.answers:
            # The agent records the answer through its tool, then the call ends.
            client.post("/tools/report_status", json={"neighbor_id": neighbor_id, "status": self.answers.pop(neighbor_id)})
        return True


@pytest.fixture(autouse=True)
def fresh():
    client.post("/api/reset")


@pytest.fixture
def line(monkeypatch: pytest.MonkeyPatch) -> FakeLine:
    fake = FakeLine()
    monkeypatch.setattr(voice, "phone_calls_configured", lambda: True)
    monkeypatch.setattr(voice, "call_resident", fake.dial)
    monkeypatch.setattr(voice, "call_ended", fake.ended)
    monkeypatch.setattr(campaign, "POLL_SECONDS", 0)
    return fake


def approve(zone: str) -> None:
    assert client.post(f"/api/orders/{zone}", json={"action": "shelter"}).status_code == 200


def residents_of(zone: str) -> list[dict]:
    return [n for n in client.get("/api/neighbors").json() if n["zone"] == zone]


def test_nothing_is_dialled_before_the_zones_order_is_approved(line: FakeLine) -> None:
    response = client.post("/api/campaigns/la-atalaya")

    assert response.status_code == 409
    assert line.dialled == []


def test_an_approved_zone_dials_each_of_its_residents_once(line: FakeLine) -> None:
    approve("la-atalaya")
    # The agent opens with what it would otherwise look up mid-call: the fire, the order, the route.
    fire_status = client.post("/tools/get_fire_status", json={"zone": "la-atalaya"}).json()["summary"]

    response = client.post("/api/campaigns/la-atalaya")

    assert response.status_code == 200
    residents = residents_of("la-atalaya")
    assert sorted(arguments["neighbor_id"] for _, arguments in line.dialled) == sorted(n["id"] for n in residents)
    for phone, arguments in line.dialled:
        resident = next(n for n in residents if n["id"] == arguments["neighbor_id"])
        assert phone.startswith("+")
        assert arguments == {
            "neighbor_id": resident["id"],
            "resident_name": resident["name"],
            "address": resident["address"],
            "zone": "la-atalaya",
            "fire_status": fire_status,
            # The order is to stay indoors: no route to give, and the order is already in fire_status.
            "route": "",
        }
        # The dashboard URL is public and the registry holds real numbers.
        assert phone not in response.text


def test_a_call_that_ends_with_nothing_reported_leaves_the_resident_as_no_answer(line: FakeLine) -> None:
    approve("la-atalaya")

    client.post("/api/campaigns/la-atalaya")

    assert {n["status"] for n in residents_of("la-atalaya")} == {"no_answer"}


def test_a_resident_who_answered_keeps_what_they_told_the_agent(line: FakeLine) -> None:
    approve("la-atalaya")
    line.answers["n01"] = "needs_rescue"

    client.post("/api/campaigns/la-atalaya")

    statuses = {n["id"]: n["status"] for n in residents_of("la-atalaya")}
    assert statuses.pop("n01") == "needs_rescue"
    assert set(statuses.values()) == {"no_answer"}


def test_a_call_that_cannot_be_placed_counts_as_no_answer(line: FakeLine) -> None:
    approve("la-atalaya")
    line.refused.add("n02")
    line.answers["n01"] = "evacuating"

    response = client.post("/api/campaigns/la-atalaya")

    assert response.status_code == 200
    # The coordinator sees the refused call, not a resident who "answered".
    assert {c["neighbor_id"]: c["call_id"] for c in response.json()}["n02"] is None
    statuses = {n["id"]: n["status"] for n in residents_of("la-atalaya")}
    assert statuses == {"n01": "evacuating", "n02": "no_answer", "n03": "no_answer"}


def test_without_a_phone_line_nothing_is_dialled(monkeypatch: pytest.MonkeyPatch) -> None:
    dialled = []
    monkeypatch.setattr(voice, "phone_calls_configured", lambda: False)
    monkeypatch.setattr(voice, "call_resident", lambda phone, arguments: dialled.append(phone) or "call")
    approve("la-atalaya")

    response = client.post("/api/campaigns/la-atalaya")

    assert response.status_code == 503
    assert dialled == []


def test_a_call_whose_status_cannot_be_read_is_still_followed_to_the_end(line: FakeLine) -> None:
    approve("la-atalaya")
    line.status_errors.add("n01")

    client.post("/api/campaigns/la-atalaya")

    assert {n["id"]: n["status"] for n in residents_of("la-atalaya")}["n01"] == "no_answer"


def test_pressing_call_again_does_not_redial_a_call_still_going(line: FakeLine, monkeypatch: pytest.MonkeyPatch) -> None:
    # The calls are still ringing: nothing has come back from the watcher yet.
    monkeypatch.setattr(campaign, "watch", lambda calls: None)
    approve("la-atalaya")

    client.post("/api/campaigns/la-atalaya")
    client.post("/api/campaigns/la-atalaya")

    assert sorted(arguments["neighbor_id"] for _, arguments in line.dialled) == ["n01", "n02", "n03"]


def test_a_reset_stops_an_earlier_campaign_from_marking_the_new_run(
    line: FakeLine, monkeypatch: pytest.MonkeyPatch
) -> None:
    watch, started = campaign.watch, []
    monkeypatch.setattr(campaign, "watch", started.append)
    approve("la-atalaya")
    client.post("/api/campaigns/la-atalaya")

    client.post("/api/reset")
    watch(started[0])  # the earlier campaign's calls end after the reset

    assert {n["status"] for n in residents_of("la-atalaya")} == {"pending"}


def test_an_approved_order_is_never_undercut_by_a_quiet_moment_on_the_slider() -> None:
    # With the slider before any forecast, the agent used to say "no risk", then "leave now".
    assert client.post("/api/replay/time", json={"at": "2026-07-22T06:00:00Z"}).status_code == 200
    approve("la-atalaya")
    order = next(o for o in client.get("/api/orders").json() if o["zone"] == "la-atalaya")

    summary = client.post("/tools/get_fire_status", json={"zone": "la-atalaya"}).json()["summary"]

    assert summary == order["message"]
