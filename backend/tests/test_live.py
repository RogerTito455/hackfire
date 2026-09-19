import httpx
import pytest
from fastapi.testclient import TestClient

from app import live
from app.main import app

client = TestClient(app)

FIRE = {"type": "Feature", "geometry": {"type": "Point", "coordinates": [-4.5, 40.4]}, "properties": {"id": "c1"}}


@pytest.fixture(autouse=True)
def fresh_cache():
    live.reset_cache()
    yield
    live.reset_cache()


def test_live_fires_are_cached(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = []
    monkeypatch.setattr(live, "_fetch_active_clusters", lambda: calls.append(1) or [FIRE])

    first = client.get("/api/live/fires").json()
    second = client.get("/api/live/fires").json()

    assert first["features"] == [FIRE] and first["stale"] is False
    assert second["fetched_at"] == first["fetched_at"]
    assert len(calls) == 1


def test_deepfire_down_with_nothing_cached_is_a_503(monkeypatch: pytest.MonkeyPatch) -> None:
    def busy() -> list[dict]:
        raise httpx.ConnectTimeout("timed out")

    monkeypatch.setattr(live, "_fetch_active_clusters", busy)
    response = client.get("/api/live/fires")
    assert response.status_code == 503
    assert "unavailable" in response.json()["detail"]


def test_deepfire_down_serves_the_last_answer_as_stale(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(live, "_fetch_active_clusters", lambda: [FIRE])
    client.get("/api/live/fires")

    def busy() -> list[dict]:
        raise httpx.ConnectTimeout("timed out")

    monkeypatch.setattr(live, "_fetch_active_clusters", busy)
    monkeypatch.setattr(live, "CACHE_SECONDS", 0)
    body = client.get("/api/live/fires").json()
    assert body["features"] == [FIRE]
    assert body["stale"] is True
