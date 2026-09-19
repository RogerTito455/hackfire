from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from app import autopilot
from app.main import app
from app.models import TriageStatus
from app.providers import sms
from app.state import state

client = TestClient(app)

SCRIPT = autopilot.parse(
    {
        "orders": [{"at": "2026-07-23T13:45:00Z", "zone_of": 1}],
        "outcomes": [
            {"at": "2026-07-23T14:00:00Z", "position": 1, "status": "evacuating", "people": 2},
            {"at": "2026-07-23T14:15:00Z", "position": 2, "status": "no_answer"},
            {"at": "2026-07-23T14:35:00Z", "position": 3, "status": "needs_rescue", "people": 2, "mobility": "wheelchair"},
            {"at": "2026-07-23T15:45:00Z", "position": 2, "status": "evacuating", "observation": "second call"},
            {"at": "2026-07-23T16:00:00Z", "position": 4, "status": "evacuating"},
            {"at": "2026-07-23T16:30:00Z", "position": 99, "status": "needs_rescue"},
        ],
    }
)


def at(hhmm: str) -> datetime:
    hours, minutes = hhmm.split(":")
    return datetime(2026, 7, 23, int(hours), int(minutes), tzinfo=UTC)


def statuses(plan: autopilot.Plan) -> dict[str, str]:
    return {nid: (o.status if o else TriageStatus.PENDING).value for nid, o in plan.outcomes.items()}


def setup_function() -> None:
    client.post("/api/reset")


# --- The pure timeline -------------------------------------------------------


def test_before_the_first_event_every_scripted_resident_is_pending_and_no_order_is_approved() -> None:
    plan = autopilot.plan(SCRIPT, state.neighbors(), at("13:30"))
    assert set(statuses(plan).values()) == {"pending"}
    assert not any(plan.zones.values())


def test_each_resident_takes_the_latest_event_at_or_before_the_moment() -> None:
    ids = [n.id for n in state.neighbors()]
    plan = autopilot.plan(SCRIPT, state.neighbors(), at("14:35"))
    assert statuses(plan) == {ids[0]: "evacuating", ids[1]: "no_answer", ids[2]: "needs_rescue", ids[3]: "pending"}
    # The retry: the resident who did not answer is evacuating after the second call.
    assert statuses(autopilot.plan(SCRIPT, state.neighbors(), at("15:45")))[ids[1]] == "evacuating"


def test_positions_the_registry_does_not_have_are_skipped() -> None:
    plan = autopilot.plan(SCRIPT, state.neighbors(), at("23:00"))
    assert len(plan.outcomes) == 4
    assert autopilot.plan(SCRIPT, state.neighbors()[:1], at("23:00")).outcomes.keys() == {state.neighbors()[0].id}


def test_a_zone_is_ordered_from_its_order_event_or_its_first_scripted_call() -> None:
    first, fourth = state.neighbors()[0], state.neighbors()[3]
    assert autopilot.plan(SCRIPT, state.neighbors(), at("13:45")).zones == {first.zone: True, fourth.zone: False}
    assert autopilot.plan(SCRIPT, state.neighbors(), at("16:00")).zones == {first.zone: True, fourth.zone: True}


def test_the_demo_script_covers_a_ten_resident_registry() -> None:
    sample = state.neighbors()
    ten = [n.model_copy(update={"id": f"x{i}"}) for i, n in enumerate(sample + sample, start=1)]
    plan = autopilot.plan(autopilot.timeline(), ten, at("20:00"))
    assert len(plan.outcomes) == 10
    assert sorted(statuses(plan).values()).count("needs_rescue") == 1
    assert "pending" not in statuses(plan).values()


def test_the_demo_script_starts_after_la_atalaya_is_first_flagged() -> None:
    script = autopilot.timeline()
    moments = [e.at for e in script.orders] + [o.at for o in script.outcomes]
    assert min(moments) > at("13:30")
    assert {o.status for o in script.outcomes} == {"evacuating", "no_answer", "needs_rescue"}


# --- The endpoint ------------------------------------------------------------


def move_clock(hhmm: str) -> None:
    assert client.post("/api/replay/time", json={"at": at(hhmm).isoformat()}).status_code == 200


def counts() -> dict[str, int]:
    result: dict[str, int] = {}
    for neighbor in client.get("/api/neighbors").json():
        result[neighbor["status"]] = result.get(neighbor["status"], 0) + 1
    return result


def test_it_is_off_by_default_and_moving_the_clock_changes_nothing() -> None:
    assert client.get("/api/autopilot").json() == {"enabled": False}
    move_clock("18:00")
    assert counts() == {"pending": 5}


def test_on_it_follows_the_clock_and_scrubbing_back_undoes() -> None:
    assert client.post("/api/autopilot", json={"enabled": True, "at": at("13:00").isoformat()}).json() == {"enabled": True}
    assert counts() == {"pending": 5}

    move_clock("14:40")
    assert counts() == {"evacuating": 1, "no_answer": 1, "needs_rescue": 1, "pending": 2}
    rescues = client.get("/api/rescues").json()
    assert [r["neighbor"]["mobility"] for r in rescues] == ["one person uses a wheelchair"]
    assert len(client.get("/api/alerts").json()) == 1
    assert any(o["approved"] for o in client.get("/api/orders").json())

    move_clock("20:00")
    assert counts() == {"evacuating": 4, "needs_rescue": 1}
    assert len(client.get("/api/alerts").json()) == 1  # one alert per rescue, however often the clock moves

    move_clock("13:00")
    assert counts() == {"pending": 5}
    assert client.get("/api/rescues").json() == []
    assert client.get("/api/alerts").json() == []
    assert not any(o["approved"] for o in client.get("/api/orders").json())


def test_a_scripted_rescue_never_texts_the_crew(monkeypatch: pytest.MonkeyPatch) -> None:
    sent: list[str] = []
    monkeypatch.setattr(sms, "configured", lambda: True)
    monkeypatch.setattr(sms, "send", lambda to, body: sent.append(body))
    client.post("/api/autopilot", json={"enabled": True, "at": at("20:00").isoformat()})
    move_clock("20:05")
    assert client.get("/api/rescues").json() != []
    assert sent == []
    assert all(alert["sent_by_sms"] is False for alert in client.get("/api/alerts").json())


def test_no_campaign_or_video_while_it_is_on() -> None:
    client.post("/api/autopilot", json={"enabled": True, "at": at("20:00").isoformat()})
    zone = client.get("/api/neighbors").json()[0]["zone"]
    assert client.post(f"/api/campaigns/{zone}").status_code == 409
    rescue = client.get("/api/rescues").json()[0]["neighbor"]["id"]
    assert client.post(f"/api/rescues/{rescue}/video").status_code == 409


def test_turning_it_off_puts_back_the_state_from_before() -> None:
    first = client.get("/api/neighbors").json()[0]["id"]
    client.post("/tools/report_status", json={"neighbor_id": first, "status": "needs_rescue", "people": 1})
    client.post("/api/autopilot", json={"enabled": True, "at": at("20:00").isoformat()})
    assert counts() == {"evacuating": 4, "needs_rescue": 1}
    assert client.post("/api/autopilot", json={"enabled": False}).json() == {"enabled": False}
    assert counts() == {"needs_rescue": 1, "pending": 4}
    assert [a["neighbor_id"] for a in client.get("/api/alerts").json()] == [first]
    move_clock("16:00")
    assert counts() == {"needs_rescue": 1, "pending": 4}


def test_reset_turns_it_off_and_restores_everything() -> None:
    client.post("/api/autopilot", json={"enabled": True, "at": at("20:00").isoformat()})
    client.post("/api/reset")
    assert client.get("/api/autopilot").json() == {"enabled": False}
    assert counts() == {"pending": 5}
    assert client.get("/api/alerts").json() == []
    assert not any(o["approved"] for o in client.get("/api/orders").json())
