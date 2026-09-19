import math

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

# Urbanización La Atalaya, El Tiemblo, from OpenStreetMap (hamlet node 1433078707).
LA_ATALAYA = (-4.46095, 40.38210)


def _km(a: tuple[float, float], b: tuple[float, float]) -> float:
    dx = (a[0] - b[0]) * 111.32 * math.cos(math.radians(b[1]))
    dy = (a[1] - b[1]) * 110.57
    return math.hypot(dx, dy)


def test_hotspots_are_served_compressed() -> None:
    response = client.get("/api/hotspots", headers={"Accept-Encoding": "gzip"})
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/geo+json"
    assert response.headers["content-encoding"] == "gzip"


def test_hotspots_are_sorted_points_with_replay_properties() -> None:
    features = client.get("/api/hotspots").json()["features"]
    assert len(features) > 1000
    times = [f["properties"]["observed_at"] for f in features]
    assert times == sorted(times)
    for feature in features[:50]:
        assert feature["geometry"]["type"] == "Point"
        assert set(feature["properties"]) >= {"observed_at", "fire_radiative_power", "confidence"}


def test_replay_shows_the_fire_near_la_atalaya_on_23_july() -> None:
    features = client.get("/api/hotspots").json()["features"]
    near = [
        f
        for f in features
        if f["properties"]["observed_at"].startswith("2026-07-23")
        and _km(tuple(f["geometry"]["coordinates"]), LA_ATALAYA) <= 5
    ]
    assert near, "no hotspots within 5 km of La Atalaya on 23 July"
