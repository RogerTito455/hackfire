"""The whole chain on another scenario: proof that nothing is tied to 23 July or El Tiemblo.

The synthetic scenario in tests/fixtures/straight-fire/ is a fire that moves straight east at 2 km/h
from 2030-03-10 00:00 UTC, somewhere else on the map, with one zone in its path (Zone A), one 12 km
off it (Zone B), three fictional residents and a router stub. Its hotspots are generated here; the
spread and the lead time come from the real pipelines. Then: impact, orders, the agent's tools, the
triage outcomes, the rescue queue, the crew alerts, the call-end safety net, the autopilot and Reset.
"""

import json
import math
import shutil
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import autopilot, impact, main, scenario
from app.main import app
from app.pipelines import build_lead_time, build_spread
from app.providers import routing, sms
from app.state import state

client = TestClient(app)

FIXTURE = Path(__file__).parent / "fixtures" / "straight-fire"
START = datetime(2030, 3, 10, tzinfo=UTC)
ORIGIN = (2.05, 45.10)  # where the fire starts
SPEED_KMH = 2.0
KM_PER_DEG_LAT = 110.57


def lonlat(x_km: float, y_km: float) -> tuple[float, float]:
    km_per_deg_lon = 111.32 * math.cos(math.radians(45.15))  # the box's middle latitude
    return round(ORIGIN[0] + x_km / km_per_deg_lon, 5), round(ORIGIN[1] + y_km / KM_PER_DEG_LAT, 5)


def straight_fire_hotspots() -> dict:
    """Five hotspots across the front every 10 minutes for 10 hours, the front 2 km further east each hour."""
    features = []
    for step in range(61):
        observed = START + timedelta(minutes=10 * step)
        front_km = SPEED_KMH * step / 6
        for index, across_km in enumerate((-0.3, -0.15, 0.0, 0.15, 0.3)):
            features.append(
                {
                    "type": "Feature",
                    "id": f"h{step}-{index}",
                    "geometry": {"type": "Point", "coordinates": list(lonlat(front_km, across_km))},
                    "properties": {
                        "observed_at": observed.strftime("%Y-%m-%dT%H:%M:%SZ"),
                        "fire_radiative_power": 20.0,
                        "confidence": "HIGH",
                        "source": "SYNTHETIC",
                        "cluster_id": "synthetic",
                    },
                }
            )
    return {"type": "FeatureCollection", "features": features}


@pytest.fixture(scope="module")
def straight_fire(tmp_path_factory):
    """The synthetic scenario, active, with its spread and lead time built by the pipelines."""
    directory = tmp_path_factory.mktemp("scenario") / "straight-fire"
    shutil.copytree(FIXTURE, directory)
    (directory / "hotspots.geojson").write_text(json.dumps(straight_fire_hotspots()), encoding="utf-8")
    previous = scenario.current()
    synthetic = scenario.load(directory / "scenario.json")
    scenario.activate(synthetic)
    build_spread.main()
    scenario.activate(synthetic)  # forget anything read before the spread existed
    build_lead_time.main()
    scenario.activate(synthetic)
    yield synthetic
    scenario.activate(previous)
    autopilot.forget()
    state.load()


@pytest.fixture(autouse=True)
def fresh_demo(straight_fire, monkeypatch: pytest.MonkeyPatch):
    """Every test starts from Reset, with a router stub and no SMS."""
    planned: list[dict] = []

    def straight_route(_client, start, end, mode, avoid):
        planned.append({"start": start, "end": end, "mode": mode, "avoid": avoid})
        return {
            "type": "Feature",
            "geometry": {"type": "LineString", "coordinates": [list(start), list(end)]},
            "properties": {
                "summary": {"distance": 12_000, "duration": 900},
                "segments": [{"steps": [{"name": "Test Road", "distance": 12_000}]}],
            },
        }

    monkeypatch.setattr(routing, "route_avoiding", straight_route)
    monkeypatch.setattr(sms, "configured", lambda: False)
    monkeypatch.setattr(main, "CALL_END_GRACE_S", 0)
    client.post("/api/reset")
    yield planned
    client.post("/api/reset")


def at(minutes: float) -> datetime:
    return START + timedelta(minutes=minutes)


def iso(moment: datetime) -> str:
    return moment.isoformat().replace("+00:00", "Z")


def neighbors() -> dict[str, dict]:
    return {n["id"]: n for n in client.get("/api/neighbors").json()}


def report(neighbor_id: str, status: str, **details) -> dict:
    response = client.post("/tools/report_status", json={"neighbor_id": neighbor_id, "status": status, **details})
    assert response.status_code == 200
    return response.json()


def test_the_dashboard_gets_the_scenario_and_its_data(straight_fire) -> None:
    info = client.get("/api/scenario").json()
    assert info["id"] == "straight-fire"
    assert info["bbox"] == [1.9, 45.0, 2.45, 45.3]
    assert info["lead_time_zone"] == "zone-a"
    assert info["scenario_time"].startswith("2030-03-10T02:00:00")

    assert len(client.get("/api/hotspots").json()["features"]) == 61 * 5
    assert [f["id"] for f in client.get("/api/zones").json()["features"]] == ["zone-a", "zone-b"]
    assert [n["id"] for n in client.get("/api/neighbors").json()] == ["r1", "r2", "r3"]
    for path in ("/api/hotspots", "/api/spread", "/api/zones", "/api/lead-time", "/api/impact"):
        assert "2026-07" not in client.get(path).text, path


def test_the_spread_reaches_the_zone_in_its_path_and_not_the_other(straight_fire) -> None:
    forecasts = impact.forecasts()
    assert forecasts, "the pipeline issued no forecast"
    assert all(f.issued_at >= straight_fire.forecast_first for f in forecasts)
    heading = json.loads(straight_fire.files.spread.read_text())["features"][0]["properties"]["heading_deg"]
    assert 80 <= heading <= 100  # east

    now = straight_fire.scenario_time
    assert impact.minutes_to_impact("zone-a", now) > 0
    assert impact.minutes_to_impact("zone-b", now) is None
    assert list(impact.timeline()["zones"]) == ["zone-a"]
    # Hours later the front has passed through Zone A.
    assert impact.minutes_to_impact("zone-a", at(6 * 60)) == 0


def test_the_lead_time_is_computed_for_the_scenarios_zone(straight_fire) -> None:
    lead = client.get("/api/lead-time").json()
    assert (lead["zone"], lead["zone_name"], lead["radius_km"]) == ("zone-a", "Zone A", 1)
    assert lead["flagged_at"] < lead["reached_at"]
    # The front reaches 1 km from Zone A (9.5 km out) at 8.5 km, after 4 h 15 min: the first hotspot
    # within the radius is the 4:20 one.
    assert lead["reached_at"] == "2030-03-10T04:20:00Z"
    assert lead["minutes"] > 0
    assert "Zone A" in lead["definition"] and "1 km of the town's outline" in lead["definition"]


def test_orders_are_proposed_approved_and_read_by_the_agent(fresh_demo) -> None:
    orders = client.get("/api/orders").json()
    assert [o["zone"] for o in orders] == ["zone-a", "zone-b"]  # the one at risk first
    zone_a = orders[0]
    assert zone_a["minutes_to_impact"] > 0 and orders[1]["minutes_to_impact"] is None
    # East Town is straight ahead of the fire; North Town is the nearest one it is not heading for.
    assert (zone_a["proposed_action"], zone_a["proposed_destination_id"]) == ("evacuate", "north-town")
    safe = {p["id"]: p["safe"] for p in client.get("/api/safe-points").json()}
    assert safe == {"north-town": True, "west-village": True, "east-town": False}

    before = client.post("/tools/get_fire_status", json={"zone": "zone-a"}).json()
    assert before["at_risk"] and "North Town" not in before["summary"]
    approved = client.post("/api/orders/zone-a", json={"action": "evacuate", "destination_id": "north-town"}).json()
    assert approved["approved"]

    status = client.post("/tools/get_fire_status", json={"zone": "zone-a"}).json()
    assert status["at_risk"] and status["minutes_to_impact"] == zone_a["minutes_to_impact"]
    assert "Zone A" in status["summary"] and "North Town" in status["summary"]
    assert client.post("/tools/get_fire_status", json={"zone": "zone-b"}).json()["at_risk"] is False

    route = client.post("/tools/get_evacuation_route", json={"address": "1 Test Street, Zone A", "mode": "car"}).json()
    assert route["geometry"]["coordinates"][-1] == [2.17737, 45.2447]
    assert route["spoken_directions"].startswith(approved["message"])
    to_north_town = fresh_demo[-1]
    assert to_north_town["avoid"] is not None  # the route was asked to keep away from the fire

    crew = client.get("/api/rescue-routes/r3").json()
    assert crew["geometry"]["coordinates"][0] == [1.98631, 45.11809]  # from the fire station


def test_call_outcomes_fill_the_rescue_queue_and_alert_the_crew() -> None:
    # A call that ends without a report leaves the resident as no_answer, for a follow-up call.
    client.post("/api/neighbors/r2/call-ended")
    assert neighbors()["r2"]["status"] == "no_answer"
    report("r2", "evacuating", people=3)

    report("r3", "no_answer")
    report("r3", "needs_rescue", people=4)
    report("r1", "needs_rescue", people=1, mobility="wheelchair")
    # The safety net never overwrites a recorded outcome.
    client.post("/api/neighbors/r1/call-ended")
    assert {k: v["status"] for k, v in neighbors().items()} == {
        "r1": "needs_rescue",
        "r2": "evacuating",
        "r3": "needs_rescue",
    }

    # Zone A has a time to impact and Zone B none: r1 comes first although r3 has more people.
    queue = client.post("/tools/get_rescue_queue").json()
    assert [(r["neighbor"]["id"], r["priority"]) for r in queue] == [("r1", 1), ("r3", 2)]
    assert queue[0]["minutes_to_impact"] > 0 and queue[1]["minutes_to_impact"] is None

    alerts = client.get("/api/alerts").json()
    assert [a["neighbor_id"] for a in alerts] == ["r1", "r3"]  # newest first
    assert alerts[0]["link"].endswith("/?rescue=r1") and "1 Test Street, Zone A" in alerts[0]["message"]
    assert not any(a["sent_by_sms"] for a in alerts)

    plan = client.get("/api/crew-plan", params={"crews": 1}).json()
    assert [a["neighbor_id"] for a in plan["assignments"]] == ["r1", "r3"]


def test_the_autopilot_follows_the_synthetic_forecast() -> None:
    entry = autopilot.first_in_forecast("zone-a")
    assert entry is not None and autopilot.first_in_forecast("zone-b") is None

    client.post("/api/autopilot", json={"enabled": True, "at": iso(entry)})
    assert all(n["status"] == "pending" for n in neighbors().values())
    assert not any(o["approved"] for o in client.get("/api/orders").json())

    # The order 10 minutes after Zone A enters the forecast, r1's call 5 minutes after that.
    client.post("/api/replay/time", json={"at": iso(entry + timedelta(minutes=15))})
    orders = {o["zone"]: o for o in client.get("/api/orders").json()}
    assert orders["zone-a"]["approved"] and orders["zone-a"]["destination_id"] == "north-town"
    assert not orders["zone-b"]["approved"]  # never in the forecast, never ordered
    assert {k: v["status"] for k, v in neighbors().items()} == {"r1": "evacuating", "r2": "pending", "r3": "pending"}

    client.post("/api/replay/time", json={"at": iso(entry + timedelta(minutes=30))})
    assert neighbors()["r2"]["status"] == "needs_rescue"
    assert [a["neighbor_id"] for a in client.get("/api/alerts").json()] == ["r2"]
    assert client.get("/api/focus").json()["neighbor_id"] == "r2"
    shown = client.get("/api/autopilot").json()
    assert [c["neighbor_id"] for c in shown["calls"]] == ["r1", "r2"]  # r3's zone is never reached
    assert list(shown["transcripts"]) == ["synthetic-rescue"]

    # Scrubbing back undoes it; turning it off puts back what was there before.
    client.post("/api/replay/time", json={"at": iso(entry)})
    assert all(n["status"] == "pending" for n in neighbors().values())
    client.post("/api/autopilot", json={"enabled": False})
    assert client.get("/api/autopilot").json()["enabled"] is False


def test_reset_restores_the_scenario(straight_fire) -> None:
    client.post("/api/orders/zone-a", json={"action": "evacuate", "destination_id": "west-village"})
    report("r1", "needs_rescue", people=2)
    client.post("/api/replay/time", json={"at": iso(at(300))})
    client.post("/api/autopilot", json={"enabled": True})

    assert client.post("/api/reset").json() == {"status": "reset", "neighbors": 3}

    assert all(n["status"] == "pending" for n in neighbors().values())
    assert not any(o["approved"] for o in client.get("/api/orders").json())
    assert client.get("/api/alerts").json() == []
    assert client.get("/api/autopilot").json()["enabled"] is False
    assert state.clock() == straight_fire.scenario_time
