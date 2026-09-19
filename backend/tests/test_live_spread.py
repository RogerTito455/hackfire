from datetime import UTC, datetime
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from app import live, live_spread
from app.main import app
from app.providers import deepfire

client = TestClient(app)


def _fire(fire_id: str, lon: float, lat: float) -> dict:
    return {"type": "Feature", "geometry": {"type": "Point", "coordinates": [lon, lat]}, "properties": {"id": fire_id}}


def _run(sim_id: str, created: str, lon: float, lat: float, status: str = "COMPLETED") -> dict:
    return {
        "id": sim_id,
        "status": status,
        "fireId": None,
        "fireName": None,
        "locationName": "Navalmoral de la Mata, Cáceres",
        "latitude": lat,
        "longitude": lon,
        "model": "elmfire",
        "durationHours": 12,
        "ensembleMembers": 1,
        "auto": True,
        "createdAt": created,
    }


def _detail(sim_id: str) -> dict:
    square = [[[[-5.53, 39.88], [-5.52, 39.88], [-5.52, 39.89], [-5.53, 39.88]]]]
    return {
        "id": sim_id,
        "status": "COMPLETED",
        "summary": {"burnedAreaM2": 6613200.0},
        "result": {
            "type": "FeatureCollection",
            "features": [
                {"type": "Feature", "geometry": {"type": "MultiPolygon", "coordinates": square}, "properties": {"hour": hour, "elapsed_seconds": hour * 3600}}
                for hour in (1, 2, 3)
            ],
        },
    }


FIRES = [_fire("c1", -5.5245, 39.8862), _fire("c2", -6.8865, 38.7154)]
RUNS = [
    _run("new", "2026-09-19T18:24:04Z", -5.5245, 39.8862),
    _run("old", "2026-09-19T12:00:00Z", -5.5250, 39.8860),  # same fire, older: dropped
    _run("far", "2026-09-19T17:00:00Z", 1.2771, 41.4789),  # no active fire within reach
    _run("nospread", "2026-09-19T18:30:00Z", -6.8865, 38.7154, status="NO_SPREAD"),
]


@pytest.fixture(autouse=True)
def fresh_cache(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    monkeypatch.setattr(live_spread, "CACHE_FILE", tmp_path / "live_spread.json")
    monkeypatch.setattr(live, "active_fires", lambda: {"features": FIRES, "stale": False})
    live_spread.reset_cache()
    yield
    live_spread.reset_cache()


def _deepfire_up(monkeypatch: pytest.MonkeyPatch, calls: list[str]) -> None:
    monkeypatch.setattr(live_spread, "_fetch_simulations", lambda since: calls.append("list") or RUNS)
    monkeypatch.setattr(
        live_spread, "_fetch_details", lambda ids: {sim_id: calls.append(sim_id) or _detail(sim_id) for sim_id in ids}
    )


def _deepfire_down(monkeypatch: pytest.MonkeyPatch) -> None:
    def busy(*_args: object) -> list[dict]:
        raise httpx.HTTPStatusError("503", request=httpx.Request("GET", "https://x"), response=httpx.Response(503))

    monkeypatch.setattr(live_spread, "_fetch_simulations", busy)


def test_latest_completed_run_per_active_fire() -> None:
    matched = live_spread.match_runs(RUNS, FIRES)
    assert {fire_id: sim["id"] for fire_id, sim in matched.items()} == {"c1": "new"}


def test_a_run_farther_than_the_match_radius_is_left_out() -> None:
    near = _run("near", "2026-09-19T10:00:00Z", -5.5245, 39.8862 + 0.02)  # ~2.2 km north
    far = _run("far", "2026-09-19T11:00:00Z", -5.5245, 39.8862 + 0.05)  # ~5.6 km north
    assert live_spread.match_runs([near, far], FIRES)["c1"]["id"] == "near"


def test_spread_endpoint_serves_hourly_polygons_and_caches(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []
    _deepfire_up(monkeypatch, calls)

    first = client.get("/api/live/spread").json()
    second = client.get("/api/live/spread").json()

    assert first["stale"] is False
    [fire] = first["fires"]
    assert fire["fire_id"] == "c1" and fire["simulation_id"] == "new"
    assert fire["name"] == "Navalmoral de la Mata, Cáceres"
    assert (fire["model"], fire["duration_hours"], fire["created_at"]) == ("elmfire", 12, "2026-09-19T18:24:04Z")
    assert [hour["hour"] for hour in fire["hours"]] == [3, 2, 1]  # largest first
    assert fire["hours"][0]["geometry"]["type"] == "MultiPolygon"
    assert second == first
    assert calls == ["list", "new"]


def test_a_completed_run_is_fetched_once(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []
    _deepfire_up(monkeypatch, calls)
    monkeypatch.setattr(live_spread, "CACHE_SECONDS", 0)

    client.get("/api/live/spread")
    client.get("/api/live/spread")

    assert calls == ["list", "new", "list"]


def test_deepfire_down_with_nothing_cached_is_a_503(monkeypatch: pytest.MonkeyPatch) -> None:
    _deepfire_down(monkeypatch)
    response = client.get("/api/live/spread")
    assert response.status_code == 503


def test_deepfire_down_serves_the_last_answer_as_stale(monkeypatch: pytest.MonkeyPatch) -> None:
    _deepfire_up(monkeypatch, [])
    good = client.get("/api/live/spread").json()

    _deepfire_down(monkeypatch)
    monkeypatch.setattr(live_spread, "CACHE_SECONDS", 0)
    live_spread._snapshot.expires = 0  # due for a refresh
    body = client.get("/api/live/spread").json()

    assert body["stale"] is True
    assert body["fires"] == good["fires"] and body["fetched_at"] == good["fetched_at"]


def test_after_a_restart_an_outage_serves_the_file(monkeypatch: pytest.MonkeyPatch) -> None:
    _deepfire_up(monkeypatch, [])
    good = client.get("/api/live/spread").json()
    assert live_spread.CACHE_FILE.exists()

    live_spread.reset_cache()  # as after a restart
    _deepfire_down(monkeypatch)
    body = client.get("/api/live/spread").json()

    assert body["stale"] is True
    assert body["fires"] == good["fires"]


def test_after_a_restart_runs_in_the_file_are_not_fetched_again(monkeypatch: pytest.MonkeyPatch) -> None:
    _deepfire_up(monkeypatch, [])
    good = client.get("/api/live/spread").json()

    live_spread.reset_cache()  # as after a restart
    calls: list[str] = []
    _deepfire_up(monkeypatch, calls)
    body = client.get("/api/live/spread").json()

    assert calls == ["list"]
    assert body["stale"] is False and body["fires"] == good["fires"]


def test_live_fires_down_is_an_outage_too(monkeypatch: pytest.MonkeyPatch) -> None:
    def down() -> dict:
        raise live.LiveUnavailable("503")

    monkeypatch.setattr(live, "active_fires", down)
    _deepfire_up(monkeypatch, [])
    assert client.get("/api/live/spread").status_code == 503


def test_provider_pages_with_the_cursor() -> None:
    pages = {
        None: {"items": [{"id": "a"}], "nextCursor": "c1"},
        "c1": {"items": [{"id": "b"}], "nextCursor": "c2"},
        "c2": {"items": [{"id": "c"}], "nextCursor": None},
    }
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json=pages[request.url.params.get("cursor")])

    with httpx.Client(transport=httpx.MockTransport(handler)) as fake:
        items = deepfire.simulations_since(fake, "token", datetime(2026, 9, 19, tzinfo=UTC), max_pages=2)

    assert [item["id"] for item in items] == ["a", "b"]  # stops at max_pages
    assert seen[0].url.path == "/v1/fire-spread/simulations"
    assert seen[0].url.params["since"] == "2026-09-19T00:00:00Z"
    assert seen[0].headers["authorization"] == "Bearer token"
    assert all(request.method == "GET" for request in seen)  # reads only; never queues a run
