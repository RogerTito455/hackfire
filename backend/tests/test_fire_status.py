from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def at(replay_time: str) -> None:
    """Move the replay clock, as the dashboard's slider does."""
    assert client.post("/api/replay/time", json={"at": replay_time}).status_code == 200


def fire_status(zone: str) -> dict:
    response = client.post("/tools/get_fire_status", json={"zone": zone})
    assert response.status_code == 200
    return response.json()


def test_la_atalaya_is_flagged_hours_ahead_of_the_fire_and_the_answer_is_no_longer_a_stub() -> None:
    at("2026-07-23T15:00:00Z")

    status = fire_status("la-atalaya")

    assert status["at_risk"] is True
    assert status["stub"] is False
    assert 180 <= status["minutes_to_impact"] <= 300  # about four hours
    assert "La Atalaya" in status["summary"]


def test_el_tiemblo_is_reached_before_la_atalaya_because_the_fire_comes_from_the_west() -> None:
    at("2026-07-23T15:00:00Z")

    assert fire_status("el-tiemblo")["minutes_to_impact"] < fire_status("la-atalaya")["minutes_to_impact"]


def test_minutes_count_down_while_the_replay_moves_within_a_forecast() -> None:
    at("2026-07-23T15:00:00Z")
    before = fire_status("la-atalaya")["minutes_to_impact"]

    at("2026-07-23T15:20:00Z")

    assert fire_status("la-atalaya")["minutes_to_impact"] == before - 20


def test_the_last_forecast_stays_valid_through_a_gap_in_the_satellite_data() -> None:
    at("2026-07-23T17:45:00Z")  # no hotspots between about 15:30 and 18:00 UTC, so no new forecast

    status = fire_status("la-atalaya")

    assert status["at_risk"] is True
    assert status["minutes_to_impact"] < 300


def test_a_zone_the_fire_does_not_reach_is_not_at_risk() -> None:
    at("2026-07-23T15:00:00Z")

    status = fire_status("nowhere")

    assert status["at_risk"] is False
    assert status["minutes_to_impact"] is None
    assert status["stub"] is False


def test_there_is_no_forecast_before_the_replay_starts_issuing_them() -> None:
    at("2026-07-22T12:00:00Z")

    status = fire_status("la-atalaya")

    assert status["at_risk"] is False
    assert "no forecast" in status["summary"].lower()


def test_before_the_dashboard_sets_a_time_the_agent_answers_for_the_demo_moment() -> None:
    assert fire_status("la-atalaya")["at_risk"] is True


def test_the_last_minutes_are_never_spoken_as_zero() -> None:
    at("2026-07-23T17:58:00Z")  # the 17:00 forecast is 58 minutes old; the school is 1 hour out

    status = fire_status("school-w332490433")

    assert status["minutes_to_impact"] == 2
    assert "0 minutes" not in status["summary"]


def test_lead_times_are_rounded_down_never_up() -> None:
    at("2026-07-23T17:20:00Z")  # El Tiemblo is 2 hours out in the 17:00 forecast, minus 20 minutes

    status = fire_status("el-tiemblo")

    assert status["minutes_to_impact"] == 100
    assert "about 1 hour" in status["summary"]


def test_no_impact_only_claims_the_horizon_the_old_forecast_still_covers() -> None:
    at("2026-07-23T17:20:00Z")  # a 6-hour forecast that is 20 minutes old covers 5 more hours and a bit

    summary = fire_status("nowhere")["summary"]

    assert "6 hours" not in summary
    assert "5 hours" in summary
