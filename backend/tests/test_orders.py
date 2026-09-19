import pytest
from fastapi.testclient import TestClient

from app import evacuation, orders
from app.main import app
from app.providers import routing

client = TestClient(app)


def feature() -> dict:
    return {
        "type": "Feature",
        "geometry": {"type": "LineString", "coordinates": [[-4.46, 40.38], [-4.40, 40.36]]},
        "properties": {"summary": {"distance": 6_000, "duration": 600}, "segments": [{"steps": []}]},
    }


@pytest.fixture(autouse=True)
def fresh(monkeypatch: pytest.MonkeyPatch):
    calls: list[tuple] = []

    def fake_route(_client, start, end, mode, avoid, *_):
        calls.append(end)
        return feature()

    monkeypatch.setattr(evacuation, "_disk_cache", lambda: {})
    monkeypatch.setattr(evacuation, "_memory", {})
    monkeypatch.setattr(routing, "route_avoiding", fake_route)
    client.post("/api/reset")
    return calls


def order_for(zone: str) -> dict:
    return next(o for o in client.get("/api/orders").json() if o["zone"] == zone)


def test_every_zone_with_residents_gets_a_proposed_order() -> None:
    zones = {n["zone"] for n in client.get("/api/neighbors").json()}
    listed = client.get("/api/orders").json()
    assert {o["zone"] for o in listed} == zones
    assert all(not o["approved"] for o in listed)


def test_the_proposal_is_a_safe_point_that_qualifies() -> None:
    order = order_for("la-atalaya")
    safe = {p["id"] for p in client.get("/api/safe-points").json() if p["safe"]}
    if order["proposed_action"] == "evacuate":
        assert order["proposed_destination_id"] in safe
    else:
        assert not safe


def test_an_approved_order_is_read_out_and_leads_every_resident_to_its_destination(fresh) -> None:
    target = next(p for p in client.get("/api/safe-points").json() if p["safe"])
    approved = client.post("/api/orders/la-atalaya", json={"action": "evacuate", "destination_id": target["id"]}).json()
    assert approved["approved"] is True
    assert approved["message"] == f"The order for La Atalaya is to leave now for {target['name']}."

    status = client.post("/tools/get_fire_status", json={"zone": "la-atalaya"}).json()
    assert status["summary"].endswith(approved["message"])

    resident = next(n for n in client.get("/api/neighbors").json() if n["zone"] == "la-atalaya")
    route = client.post("/tools/get_evacuation_route", json={"address": resident["address"], "mode": "car"}).json()
    assert route["spoken_directions"].startswith(approved["message"])
    assert fresh[-1] == (target["lon"], target["lat"])


def test_a_shelter_order_replaces_the_route() -> None:
    client.post("/api/orders/el-tiemblo", json={"action": "shelter"})
    resident = next(n for n in client.get("/api/neighbors").json() if n["zone"] == "el-tiemblo")
    route = client.get(f"/api/routes/{resident['id']}?mode=walking").json()
    assert route["geometry"] is None
    assert route["spoken_directions"] == "The order for El Tiemblo is to stay indoors until the emergency services say otherwise."


def test_unknown_zone_or_destination_is_a_404() -> None:
    assert client.post("/api/orders/atlantis", json={"action": "shelter"}).status_code == 404
    bad = client.post("/api/orders/la-atalaya", json={"action": "evacuate", "destination_id": "nowhere"})
    assert bad.status_code == 404


def test_reset_clears_the_orders() -> None:
    client.post("/api/orders/el-tiemblo", json={"action": "shelter"})
    client.post("/api/reset")
    assert not order_for("el-tiemblo")["approved"]
    assert orders.approved_order("el-tiemblo") is None


def test_unapproved_zones_keep_each_residents_nearest_safe_point() -> None:
    resident = next(n for n in client.get("/api/neighbors").json() if n["zone"] == "la-atalaya")
    route = client.get(f"/api/routes/{resident['id']}?mode=car").json()
    assert not route["spoken_directions"].startswith("The order for")
