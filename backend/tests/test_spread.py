from datetime import datetime

from fastapi.testclient import TestClient

from app import spread, zones
from app.config import settings
from app.main import app, fire_summary

client = TestClient(app)

# Early afternoon on 23 July: the front runs east-north-east towards El Tiemblo and La Atalaya.
AFTERNOON = datetime.fromisoformat("2026-07-23T14:00:00+00:00")
# Before the first hotspot (22 July 11:08 UTC): nothing to tell a direction from.
BEFORE = datetime.fromisoformat("2026-07-22T08:00:00+00:00")


def test_front_heads_east_north_east_in_the_afternoon() -> None:
    motion = spread.front_motion(AFTERNOON)
    assert motion is not None
    assert 45 <= motion.bearing_deg <= 100
    assert 500 <= motion.speed_m_per_h <= 5_000


def test_no_direction_without_recent_hotspots() -> None:
    assert spread.front_motion(BEFORE) is None


def test_la_atalaya_is_flagged_hours_ahead_in_the_afternoon() -> None:
    minutes = zones.minutes_to_impact("la-atalaya", AFTERNOON)
    assert minutes is not None and 60 <= minutes <= spread.HORIZON_H * 60


def test_cone_hours_are_nested() -> None:
    cone = spread.hourly_cone(AFTERNOON)
    assert [hour for hour, _ in cone] == list(range(1, spread.HORIZON_H + 1))
    for (_, inner), (_, outer) in zip(cone, cone[1:]):
        assert outer.area >= inner.area


def test_fire_status_is_real_for_la_atalaya() -> None:
    status = client.post("/tools/get_fire_status", json={"zone": "la-atalaya"}).json()
    assert status["stub"] is False
    assert status["minutes_to_impact"] == zones.minutes_to_impact("la-atalaya", settings.scenario_time)
    assert status["at_risk"] == (status["minutes_to_impact"] is not None)
    assert "La Atalaya" in status["summary"]


def test_unknown_zone_is_a_404() -> None:
    assert client.post("/tools/get_fire_status", json={"zone": "atlantis"}).status_code == 404


def test_summaries_read_well() -> None:
    motion = spread.front_motion(AFTERNOON)
    assert fire_summary("La Atalaya", 0, 0.0, motion) == "The fire has already reached La Atalaya."
    text = fire_summary("La Atalaya", 130, 4.2, motion)
    assert text.startswith("The burned area is about 4 kilometres from La Atalaya. The fire is moving")
    assert text.endswith("it could reach La Atalaya in about 2 hours and 10 minutes.")
    assert "not heading towards" in fire_summary("Cebreros", None, 6.0, motion)
    assert "no clear direction" in fire_summary("Cebreros", None, 6.0, None).replace("do not show a clear", "no clear")


def test_spread_endpoint_returns_hours_outermost_first() -> None:
    body = client.get("/api/spread", params={"at": AFTERNOON.isoformat()}).json()
    assert [f["properties"]["hour"] for f in body["features"]] == list(range(spread.HORIZON_H, 0, -1))
    assert body["motion"]["bearing_deg"] > 0


def test_spread_is_empty_without_a_direction() -> None:
    body = client.get("/api/spread", params={"at": BEFORE.isoformat()}).json()
    assert body["features"] == [] and body["motion"] is None


def test_zone_risk_lists_every_zone_soonest_first() -> None:
    body = client.get("/api/zones/risk", params={"at": AFTERNOON.isoformat()}).json()
    minutes = [z["minutes_to_impact"] for z in body["zones"]]
    known = [m for m in minutes if m is not None]
    assert known == sorted(known)
    assert minutes[len(known):] == [None] * (len(minutes) - len(known))
    assert {z["id"] for z in body["zones"]} >= {"la-atalaya", "el-tiemblo"}
    assert client.get("/api/zones").json()["type"] == "FeatureCollection"


def test_zone_risk_before_the_first_hotspot_is_empty_not_an_error() -> None:
    body = client.get("/api/zones/risk", params={"at": BEFORE.isoformat()})
    assert body.status_code == 200
    assert all(z["minutes_to_impact"] is None for z in body.json()["zones"])
