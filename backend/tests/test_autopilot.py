from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from app import autopilot
from app.main import app
from app.models import AutopilotTranscript, AutopilotTurn, TriageStatus
from app.providers import sms
from app.state import state

client = TestClient(app)

SCRIPT = autopilot.parse(
    {
        "order_after_minutes": 30,
        "orders": [{"zone_of": 1, "after_minutes": 15}],
        "outcomes": [
            {"position": 1, "after_minutes": 15, "status": "evacuating", "people": 2},
            {"position": 2, "after_minutes": 30, "status": "no_answer"},
            {"position": 3, "after_minutes": 50, "status": "needs_rescue", "people": 2, "mobility": "wheelchair"},
            {"position": 2, "after_minutes": 120, "status": "evacuating", "observation": "secondCall"},
            {"position": 4, "after_minutes": 15, "status": "evacuating"},
            {"position": 99, "after_minutes": 0, "status": "needs_rescue"},
        ],
        "calls": {"evacuating": ["parent"], "no_answer": ["wrong"], "needs_rescue": ["wheelchair", "stays"]},
    }
)


def at(hhmm: str) -> datetime:
    hours, minutes = hhmm.split(":")
    return datetime(2026, 7, 23, int(hours), int(minutes), tzinfo=UTC)


# The pure tests choose when each zone enters the forecast; in the cached data both enter at 13:30.
ENTRIES = {"la-atalaya": at("13:30"), "el-tiemblo": at("15:00")}


def plan_at(hhmm: str, residents=None, entries=ENTRIES) -> autopilot.Plan:
    schedule = autopilot.schedule(SCRIPT, residents if residents is not None else state.neighbors(), entries)
    return autopilot.plan(schedule, at(hhmm))


def statuses(plan: autopilot.Plan) -> dict[str, str]:
    return {nid: (c.outcome.status if c else TriageStatus.PENDING).value for nid, c in plan.outcomes.items()}


def recorded(status: str) -> AutopilotTranscript:
    return AutopilotTranscript(scenario="x", status=TriageStatus(status), turns=[AutopilotTurn(speaker="agent", text="Hola")])


def setup_function() -> None:
    client.post("/api/reset")


# --- The pure timeline -------------------------------------------------------


def test_before_a_zone_enters_the_forecast_nobody_there_is_called_and_no_order_is_approved() -> None:
    plan = plan_at("13:30")
    assert set(statuses(plan).values()) == {"pending"}
    assert not any(plan.zones.values())


def test_the_order_and_the_calls_follow_the_zones_entry_into_the_forecast() -> None:
    ids = [n.id for n in state.neighbors()]
    # La Atalaya enters at 13:30: its order at +15 (13:45), then calls 15, 30 and 50 minutes after the order.
    assert plan_at("13:44").zones["la-atalaya"] is False
    assert plan_at("13:45").zones["la-atalaya"] is True
    assert statuses(plan_at("14:35")) == {ids[0]: "evacuating", ids[1]: "no_answer", ids[2]: "needs_rescue", ids[3]: "pending"}
    # A later entry moves the zone's order and calls by the same amount.
    later = {**ENTRIES, "la-atalaya": at("16:00")}
    assert set(statuses(plan_at("14:35", entries=later)).values()) == {"pending"}
    assert statuses(plan_at("17:04", entries=later))[ids[2]] == "pending"
    assert statuses(plan_at("17:05", entries=later))[ids[2]] == "needs_rescue"


def test_a_zone_no_order_names_is_ordered_after_the_default_offset() -> None:
    fourth = state.neighbors()[3]
    # El Tiemblo enters at 15:00 and no order event names it: the default 30 minutes, 15:30, called at 15:45.
    assert plan_at("15:29").zones[fourth.zone] is False
    assert plan_at("15:30").zones[fourth.zone] is True
    assert statuses(plan_at("15:44"))[fourth.id] == "pending"
    assert statuses(plan_at("15:45"))[fourth.id] == "evacuating"


def test_each_resident_takes_the_latest_outcome_at_or_before_the_moment() -> None:
    second = state.neighbors()[1].id
    assert statuses(plan_at("14:15"))[second] == "no_answer"
    # The retry: the resident who did not answer is evacuating after the second call.
    assert statuses(plan_at("15:45"))[second] == "evacuating"


def test_residents_of_a_zone_the_forecast_never_reaches_are_not_called() -> None:
    plan = plan_at("23:00", entries={"la-atalaya": at("13:30")})
    assert {n.zone for n in state.neighbors() if n.id in plan.outcomes} == {"la-atalaya"}
    assert "el-tiemblo" not in plan.zones


def test_positions_the_registry_does_not_have_are_skipped() -> None:
    assert len(plan_at("23:00").outcomes) == 4
    first = state.neighbors()[0]
    assert plan_at("23:00", residents=[first]).outcomes.keys() == {first.id}


def test_each_outcome_gets_a_transcript_of_its_own_status_cycling_through_them() -> None:
    all_four = {
        "parent": recorded("evacuating"),
        "wrong": recorded("no_answer"),
        "wheelchair": recorded("needs_rescue"),
        "stays": recorded("needs_rescue"),
    }
    assert autopilot.assign_transcripts(SCRIPT, all_four) == ["parent", "wrong", "wheelchair", "parent", "parent", "stays"]


def test_a_missing_transcript_or_one_that_ended_another_way_is_never_shown() -> None:
    # "wheelchair" ended as evacuating: a rescue's card must not show a call that ended otherwise.
    mixed = {"parent": recorded("evacuating"), "wheelchair": recorded("evacuating"), "stays": recorded("needs_rescue")}
    assert autopilot.assign_transcripts(SCRIPT, mixed) == ["parent", None, "stays", "parent", "parent", "stays"]
    assert autopilot.assign_transcripts(SCRIPT, {}) == [None] * len(SCRIPT.outcomes)


def test_the_schedule_carries_each_calls_transcript_oldest_first() -> None:
    schedule = autopilot.schedule(SCRIPT, state.neighbors(), ENTRIES, {"wheelchair": recorded("needs_rescue")})
    assert [c.at for c in schedule.calls] == sorted(c.at for c in schedule.calls)
    rescue = next(c for c in schedule.calls if c.outcome.status == TriageStatus.NEEDS_RESCUE)
    assert (rescue.at, rescue.transcript) == (at("14:35"), "wheelchair")
    assert {c.transcript for c in schedule.calls if c.outcome.status != TriageStatus.NEEDS_RESCUE} == {None}


def test_recorded_calls_without_a_status_or_turns_are_left_out() -> None:
    raw = {
        "calls": {
            "ok": {"status": "needs_rescue", "turns": [{"speaker": "agent", "text": "Hola"}]},
            "never-recorded": {"status": None, "turns": [{"speaker": "agent", "text": "Hola"}]},
            "empty": {"status": "evacuating", "turns": []},
        }
    }
    assert list(autopilot.parse_transcripts(raw)) == ["ok"]


def test_the_demo_script_covers_a_ten_resident_registry() -> None:
    sample = state.neighbors()
    ten = [n.model_copy(update={"id": f"x{i}"}) for i, n in enumerate(sample + sample, start=1)]
    entries = {zone: autopilot.first_in_forecast(zone) for zone in {n.zone for n in ten}}
    plan = autopilot.plan(autopilot.schedule(autopilot.timeline(), ten, entries), at("20:00"))
    assert len(plan.outcomes) == 10
    assert sorted(statuses(plan).values()).count("needs_rescue") == 1
    assert "pending" not in statuses(plan).values()


def test_the_demo_script_starts_after_la_atalaya_is_first_flagged() -> None:
    assert autopilot.first_in_forecast("la-atalaya") == at("13:30")
    schedule = autopilot.current_schedule()
    assert min(list(schedule.orders.values()) + [c.at for c in schedule.calls]) > at("13:30")
    assert {c.outcome.status for c in schedule.calls} == {"evacuating", "no_answer", "needs_rescue"}


def test_the_recorded_calls_are_simulated_residents_and_ended_as_the_script_lists_them() -> None:
    script, calls = autopilot.timeline(), autopilot.transcripts()
    registry = [n.name for n in state.neighbors()] + [n.address for n in state.neighbors()]
    assert any(key in calls for keys in script.calls.values() for key in keys)
    for status, keys in script.calls.items():
        for key in (k for k in keys if k in calls):
            assert calls[key].status == status
            assert calls[key].turns[0].speaker == "agent"
            assert not any(entry in turn.text for turn in calls[key].turns for entry in registry)


# --- The endpoint ------------------------------------------------------------


def move_clock(hhmm: str) -> None:
    assert client.post("/api/replay/time", json={"at": at(hhmm).isoformat()}).status_code == 200


def counts() -> dict[str, int]:
    result: dict[str, int] = {}
    for neighbor in client.get("/api/neighbors").json():
        result[neighbor["status"]] = result.get(neighbor["status"], 0) + 1
    return result


def residents() -> int:
    """However many the registry holds: the script names them by position, not by id."""
    return len(client.get("/api/neighbors").json())


def test_it_is_off_by_default_and_moving_the_clock_changes_nothing() -> None:
    assert client.get("/api/autopilot").json() == {"enabled": False, "calls": [], "transcripts": {}}
    move_clock("18:00")
    assert counts() == {"pending": residents()}


def test_on_it_follows_the_clock_and_scrubbing_back_undoes() -> None:
    assert client.post("/api/autopilot", json={"enabled": True, "at": at("13:00").isoformat()}).json()["enabled"] is True
    assert counts() == {"pending": residents()}

    move_clock("14:40")
    assert counts() == {"evacuating": 1, "no_answer": 1, "needs_rescue": 1, "pending": residents() - 3}
    rescues = client.get("/api/rescues").json()
    assert [r["neighbor"]["mobility"] for r in rescues] == ["one person uses a wheelchair"]
    assert len(client.get("/api/alerts").json()) == 1
    assert any(o["approved"] for o in client.get("/api/orders").json())

    move_clock("20:00")
    assert counts() == {"evacuating": residents() - 1, "needs_rescue": 1}
    assert len(client.get("/api/alerts").json()) == 1  # one alert per rescue, however often the clock moves

    move_clock("13:00")
    assert counts() == {"pending": residents()}
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
    assert counts() == {"evacuating": residents() - 1, "needs_rescue": 1}
    assert client.post("/api/autopilot", json={"enabled": False}).json()["enabled"] is False
    assert counts() == {"needs_rescue": 1, "pending": residents() - 1}
    assert [a["neighbor_id"] for a in client.get("/api/alerts").json()] == [first]
    move_clock("16:00")
    assert counts() == {"needs_rescue": 1, "pending": residents() - 1}


def test_reset_turns_it_off_and_restores_everything() -> None:
    client.post("/api/autopilot", json={"enabled": True, "at": at("20:00").isoformat()})
    client.post("/api/reset")
    assert client.get("/api/autopilot").json() == {"enabled": False, "calls": [], "transcripts": {}}
    assert counts() == {"pending": residents()}
    assert client.get("/api/alerts").json() == []
    assert not any(o["approved"] for o in client.get("/api/orders").json())


def test_on_it_lists_the_scripted_calls_with_the_transcripts_they_name() -> None:
    body = client.post("/api/autopilot", json={"enabled": True, "at": at("13:00").isoformat()}).json()
    assert [c["at"] for c in body["calls"]] == sorted(c["at"] for c in body["calls"])
    assert len(body["calls"]) == residents() + 1  # every resident, one of them called twice
    named = {c["transcript"] for c in body["calls"] if c["transcript"]}
    assert named == set(body["transcripts"])
    for call in body["calls"]:
        if call["transcript"]:
            assert body["transcripts"][call["transcript"]]["status"] == call["status"]


def test_a_scripted_rescue_takes_the_agent_focus_until_scrubbed_back() -> None:
    client.post("/api/autopilot", json={"enabled": True, "at": at("13:00").isoformat()})
    assert client.get("/api/focus").json() is None
    move_clock("14:40")
    focus = client.get("/api/focus").json()
    rescue = client.get("/api/rescues").json()[0]
    assert (focus["neighbor_id"], focus["rescue_id"]) == (rescue["neighbor"]["id"], rescue["rescue_id"])
    move_clock("15:00")
    assert client.get("/api/focus").json() == focus  # once per landing, not on every move
    move_clock("14:00")
    assert client.get("/api/focus").json() is None
    move_clock("14:40")
    assert client.get("/api/focus").json()["at"] != focus["at"]  # landing again is followed again
    client.post("/api/autopilot", json={"enabled": False})
    assert client.get("/api/focus").json() is None
