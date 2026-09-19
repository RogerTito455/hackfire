import json

import httpx
import pytest
from fastapi.testclient import TestClient
from shapely.geometry import shape

from app import evacuation, geo
from app.config import DATA_DIR, settings
from app.main import app
from app.models import Neighbor, TravelMode
from app.providers import routing

client = TestClient(app)
REAL_DISK_CACHE = evacuation._disk_cache


def fake_feature(distance: float = 12_600, duration: float = 1_080) -> dict:
    return {
        "type": "Feature",
        "geometry": {"type": "LineString", "coordinates": [[-4.4588, 40.3829], [-4.4652, 40.4552]]},
        "properties": {
            "summary": {"distance": distance, "duration": duration},
            "segments": [
                {
                    "steps": [
                        {"distance": 120, "name": "Calle del Narcea"},
                        {"distance": 5_900, "name": "AV-512"},
                        {"distance": 4_000, "name": "N-403"},
                        {"distance": 2_000, "name": "AV-512"},
                        {"distance": 0, "name": "-"},
                    ]
                }
            ],
        },
    }


@pytest.fixture(autouse=True)
def isolated_routing(monkeypatch: pytest.MonkeyPatch):
    """No disk cache, no memory cache, and a recorder instead of openrouteservice."""
    calls: list[dict] = []

    def fake_route(_client, start, end, mode, avoid):
        calls.append({"start": start, "end": end, "mode": mode, "avoid": avoid})
        return fake_feature()

    monkeypatch.setattr(evacuation, "_disk_cache", lambda: {})
    monkeypatch.setattr(evacuation, "_memory", {})
    monkeypatch.setattr(routing, "route_avoiding", fake_route)
    client.post("/api/reset")
    return calls


def first_neighbor() -> dict:
    return client.get("/api/neighbors").json()[0]


def test_avoid_polygon_fits_openrouteservice_limits() -> None:
    home, cebreros = (-4.4588, 40.3829), (-4.46516, 40.45515)
    avoid = evacuation.avoid_polygon(home, cebreros, settings.scenario_time)
    assert avoid is not None
    area = geo.to_metres(shape(avoid))
    min_x, min_y, max_x, max_y = area.bounds
    assert area.area <= 200e6
    assert max_x - min_x <= 20_000 and max_y - min_y <= 20_000
    assert not area.contains(geo.point_m(*home))


def test_evacuation_route_tool_returns_a_real_route(isolated_routing) -> None:
    response = client.post(
        "/tools/get_evacuation_route", json={"address": first_neighbor()["address"], "mode": "walking"}
    )
    assert response.status_code == 200
    route = response.json()
    assert route["stub"] is False
    assert route["geometry"]["type"] == "LineString"
    assert route["distance_m"] == 12_600
    assert isolated_routing[0]["mode"] == TravelMode.WALKING
    assert route["spoken_directions"].startswith(f"Walk to {evacuation.safest_point(settings.scenario_time).name}")


def test_spoken_directions_name_the_main_roads_in_order() -> None:
    text = evacuation.spoken_directions(fake_feature(), TravelMode.CAR, "Cebreros", avoided_fire=True)
    assert text.startswith("Drive to Cebreros along AV-512, then N-403, then AV-512.")
    assert "about 13 kilometres, around 18 minutes by car" in text
    assert "keeps away from the area the fire has already burned" in text


def test_long_walks_are_said_in_hours() -> None:
    text = evacuation.spoken_directions(fake_feature(duration=8_385), TravelMode.WALKING, "Cebreros", False)
    assert "around 2 hours and 20 minutes on foot." in text
    assert "fire" not in text


def test_unknown_address_is_a_404() -> None:
    response = client.post("/tools/get_evacuation_route", json={"address": "Nowhere 1", "mode": "car"})
    assert response.status_code == 404


def test_routing_outage_is_a_503(monkeypatch: pytest.MonkeyPatch) -> None:
    def down(*_args):
        raise httpx.ConnectTimeout("timed out")

    monkeypatch.setattr(routing, "route_avoiding", down)
    response = client.post("/tools/get_evacuation_route", json={"address": first_neighbor()["address"]})
    assert response.status_code == 503


def test_no_safe_route_is_said_plainly(monkeypatch: pytest.MonkeyPatch) -> None:
    def blocked(*_args):
        raise routing.NoRouteFound("no route")

    monkeypatch.setattr(routing, "route_avoiding", blocked)
    route = client.post("/tools/get_evacuation_route", json={"address": first_neighbor()["address"]}).json()
    assert route["geometry"] is None
    assert route["spoken_directions"].startswith("No route that keeps away from the fire was found.")


def test_routes_are_planned_once(isolated_routing) -> None:
    neighbor_id = first_neighbor()["id"]
    client.get(f"/api/routes/{neighbor_id}?mode=car")
    client.get(f"/api/routes/{neighbor_id}?mode=car")
    assert len(isolated_routing) == 1


def test_rescue_route_starts_at_the_crew_base(isolated_routing) -> None:
    neighbor = first_neighbor()
    client.post("/tools/report_status", json={"neighbor_id": neighbor["id"], "status": "needs_rescue"})
    rescue_id = client.post("/tools/get_rescue_queue").json()[0]["rescue_id"]
    route = client.post("/tools/get_rescue_route", json={"rescue_id": rescue_id}).json()
    base = evacuation.crew_base()
    assert isolated_routing[0]["start"] == (base.lon, base.lat)
    assert isolated_routing[0]["end"] == (neighbor["lon"], neighbor["lat"])
    assert route["spoken_directions"].startswith(f"Drive to {neighbor['address']}")


def test_fire_area_is_a_polygon_up_to_the_scenario_time() -> None:
    area = client.get("/api/fire-area").json()
    assert area["geometry"]["type"] in ("Polygon", "MultiPolygon")
    assert area["properties"]["until"] == settings.scenario_time.isoformat()


def test_committed_cache_covers_the_sample_registry(monkeypatch: pytest.MonkeyPatch) -> None:
    """The demo must not need openrouteservice for the sample residents."""
    monkeypatch.setattr(evacuation, "_disk_cache", REAL_DISK_CACHE)

    def down(*_args):
        raise httpx.ConnectTimeout("ORS must not be called")

    monkeypatch.setattr(routing, "route_avoiding", down)
    sample = json.loads((DATA_DIR / "neighbors.sample.json").read_text(encoding="utf-8"))
    for raw in sample:
        neighbor = Neighbor(**raw)
        for mode in TravelMode:
            assert evacuation.evacuation_route(neighbor, mode).geometry is not None
        assert evacuation.rescue_route(neighbor).geometry is not None


def test_dashboard_rescue_route_starts_at_the_crew_base(isolated_routing) -> None:
    neighbor = first_neighbor()
    route = client.get(f"/api/rescue-routes/{neighbor['id']}").json()
    assert isolated_routing[0]["start"] == (evacuation.crew_base().lon, evacuation.crew_base().lat)
    assert route["mode"] == "car"
    assert client.get("/api/rescue-routes/nobody").status_code == 404
