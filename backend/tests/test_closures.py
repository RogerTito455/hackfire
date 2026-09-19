"""Road closures: the coordinator marks a road cut, and every route after that goes around it."""

import pytest
from fastapi.testclient import TestClient
from shapely.geometry import Point, shape

from app import evacuation, geo
from app.config import settings
from app.main import app
from app.providers import routing

client = TestClient(app)


def fake_feature(duration: float = 1_080, line: list | None = None) -> dict:
    """An openrouteservice route; the default runs straight north from La Atalaya."""
    return {
        "type": "Feature",
        "geometry": {"type": "LineString", "coordinates": line or [[-4.4588, 40.3829], [-4.4652, 40.4552]]},
        "properties": {
            "summary": {"distance": 12_600, "duration": duration},
            "segments": [{"steps": [{"distance": 12_600, "name": "AV-512"}]}],
        },
    }

NEAR_LA_ATALAYA = {"lat": 40.39, "lon": -4.44}


@pytest.fixture(autouse=True)
def isolated_routing(monkeypatch: pytest.MonkeyPatch):
    """No caches, and a recorder instead of openrouteservice."""
    calls: list[dict] = []

    def fake_route(_client, start, end, mode, avoid, *_):
        calls.append({"start": start, "end": end, "mode": mode, "avoid": avoid})
        return fake_feature()

    monkeypatch.setattr(evacuation, "_disk_cache", lambda: {})
    monkeypatch.setattr(evacuation, "_memory", {})
    monkeypatch.setattr(routing, "route_avoiding", fake_route)
    client.post("/api/reset")
    return calls


def first_neighbor() -> dict:
    return client.get("/api/neighbors").json()[0]


def test_a_route_asked_after_a_closure_goes_around_it(isolated_routing) -> None:
    neighbor = first_neighbor()["id"]
    client.get(f"/api/routes/{neighbor}")

    before = len(isolated_routing)
    client.post("/api/closures", json=NEAR_LA_ATALAYA)
    client.get(f"/api/routes/{neighbor}")

    after = isolated_routing[before:]
    assert after, "the route from before the closure must not come back from the cache"
    closed = Point(NEAR_LA_ATALAYA["lon"], NEAR_LA_ATALAYA["lat"])
    assert all(shape(call["avoid"]).contains(closed) for call in after)


def safe_points_nearest_first(neighbor: dict) -> list:
    here = geo.point_m(neighbor["lon"], neighbor["lat"])
    return sorted(evacuation.safe_points(settings.scenario_time), key=lambda p: here.distance(geo.point_m(p.lon, p.lat)))


def cut_off(monkeypatch: pytest.MonkeyPatch, unreachable, minutes: dict) -> None:
    """openrouteservice with no way to `unreachable`, and `minutes` of driving to the others."""

    def fake_route(_client, start, end, mode, avoid, *_):
        if end == (unreachable.lon, unreachable.lat):
            raise routing.NoRouteFound("every way in is avoided")
        return fake_feature(duration=minutes.get(end, 30) * 60)

    monkeypatch.setattr(routing, "route_avoiding", fake_route)


def test_when_a_closure_cuts_off_the_nearest_safe_point_the_fastest_reachable_one_is_chosen(monkeypatch) -> None:
    neighbor = first_neighbor()
    nearest, second, third = safe_points_nearest_first(neighbor)[:3]
    cut_off(monkeypatch, nearest, {(second.lon, second.lat): 25, (third.lon, third.lat): 15})
    client.post("/api/closures", json=NEAR_LA_ATALAYA)

    route = client.get(f"/api/routes/{neighbor['id']}").json()

    assert third.name in route["spoken_directions"]
    assert route["duration_s"] == 15 * 60


def test_when_a_closure_cuts_off_the_ordered_destination_the_resident_is_told_and_sent_elsewhere(monkeypatch) -> None:
    neighbor = first_neighbor()
    ordered, *others = safe_points_nearest_first(neighbor)[:3]
    approved = client.post(f"/api/orders/{neighbor['zone']}", json={"action": "evacuate", "destination_id": ordered.id})
    assert approved.status_code == 200
    cut_off(monkeypatch, ordered, {(p.lon, p.lat): 20 for p in others})
    client.post("/api/closures", json=NEAR_LA_ATALAYA)

    route = client.get(f"/api/routes/{neighbor['id']}").json()

    assert route["geometry"] is not None
    assert f"The road to {ordered.name} is closed." in route["spoken_directions"]
    assert others[0].name in route["spoken_directions"]


def test_closing_a_road_names_the_residents_already_leaving_through_it() -> None:
    neighbor = first_neighbor()
    client.post("/tools/report_status", json={"neighbor_id": neighbor["id"], "status": "evacuating", "people": 2})
    on_their_way = {"lat": 40.419, "lon": -4.462}  # halfway along the fake route
    elsewhere = {"lat": 40.39, "lon": -4.40}

    assert client.post("/api/closures", json=elsewhere).json()["affected"] == []
    assert client.post("/api/closures", json=on_their_way).json()["affected"] == [neighbor["id"]]


def test_a_crew_is_never_sent_through_a_closed_road(monkeypatch) -> None:
    asked: list[dict | None] = []

    def fire_and_closure_block_every_way(_client, start, end, mode, avoid, *_):
        asked.append(avoid)
        if len(asked) == 1:
            raise routing.NoRouteFound("every way in is avoided")
        return fake_feature()

    monkeypatch.setattr(routing, "route_avoiding", fire_and_closure_block_every_way)
    client.post("/api/closures", json=NEAR_LA_ATALAYA)

    route = client.get(f"/api/rescue-routes/{first_neighbor()['id']}").json()

    closed = Point(NEAR_LA_ATALAYA["lon"], NEAR_LA_ATALAYA["lat"])
    assert route["geometry"] is not None
    assert len(asked) == 2 and all(avoid is not None and shape(avoid).contains(closed) for avoid in asked)
