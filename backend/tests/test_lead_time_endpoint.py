from datetime import datetime

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def parse(moment: str) -> datetime:
    return datetime.fromisoformat(moment)


def test_lead_time_endpoint_serves_the_number_the_pitch_quotes_with_its_definition() -> None:
    response = client.get("/api/lead-time")

    assert response.status_code == 200
    body = response.json()
    assert body["zone"] == "la-atalaya"
    assert body["radius_km"] == 3
    # The first forecast that puts La Atalaya in the fire's path, and the first hotspot within 3 km
    # of the estate's outline (MTG, 19:38 UTC), both checked by hand against the cached data.
    assert body["flagged_at"] == "2026-07-23T13:30:00Z"
    assert body["reached_at"].startswith("2026-07-23T19:3")
    assert 360 <= body["minutes"] <= 375
    assert body["minutes"] == int((parse(body["reached_at"]) - parse(body["flagged_at"])).total_seconds() // 60)
    assert "satellite" in body["definition"].lower()
    assert "authorities" in body["definition"].lower()  # the number claims nothing about official warnings
