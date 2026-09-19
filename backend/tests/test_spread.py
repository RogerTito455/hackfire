import math
from datetime import UTC, datetime, timedelta

from app.spread import Hotspot, forecast

ISSUED_AT = datetime(2026, 7, 23, 15, 0, tzinfo=UTC)
FRONT = (-4.60, 40.38)  # (lon, lat) of the front at ISSUED_AT

KM_PER_DEG_LAT = 110.57
KM_PER_DEG_LON = 111.32 * math.cos(math.radians(FRONT[1]))


def marching_fire(speed_kmh: float, towards: str, hours: float = 4) -> list[Hotspot]:
    """Satellite detections every 10 minutes along a 1.2 km wide front advancing at a known speed."""
    hotspots = []
    for step in range(int(hours * 6) + 1):
        minutes_before = step * 10
        observed_at = ISSUED_AT - timedelta(minutes=minutes_before)
        along_km = -speed_kmh * minutes_before / 60
        for across_km in (-0.6, -0.3, 0.0, 0.3, 0.6):
            east_km, north_km = (along_km, across_km) if towards == "east" else (across_km, along_km)
            hotspots.append(
                Hotspot(
                    lon=FRONT[0] + east_km / KM_PER_DEG_LON,
                    lat=FRONT[1] + north_km / KM_PER_DEG_LAT,
                    observed_at=observed_at,
                )
            )
    return hotspots


def test_front_marching_east_at_3_kmh_is_predicted_9_km_further_after_3_hours() -> None:
    result = forecast(marching_fire(3, "east"), ISSUED_AT)

    assert result is not None
    reach_km = (result.spread[3].bounds[2] - FRONT[0]) * KM_PER_DEG_LON
    assert 8 <= reach_km <= 10.5


def test_front_marching_north_is_predicted_north_and_not_east() -> None:
    result = forecast(marching_fire(2, "north"), ISSUED_AT)

    assert result is not None
    north_km = (result.spread[3].bounds[3] - FRONT[1]) * KM_PER_DEG_LAT
    east_km = (result.spread[3].bounds[2] - FRONT[0]) * KM_PER_DEG_LON
    assert 5 <= north_km <= 7.5  # 2 km/h for 3 h is 6 km
    assert east_km < 3  # only the flank spread and the pixel padding, well short of the head
    assert abs(result.heading_deg - 0) < 10 or abs(result.heading_deg - 360) < 10


def test_each_hour_contains_the_previous_one() -> None:
    result = forecast(marching_fire(3, "east"), ISSUED_AT, horizon_hours=6)

    assert result is not None
    assert len(result.spread) == 7  # now, plus one polygon per hour ahead
    for earlier, later in zip(result.spread, result.spread[1:]):
        assert later.contains(earlier)


def test_hotspots_after_the_issue_time_are_ignored() -> None:
    past = marching_fire(3, "east")
    future = [
        Hotspot(lon=FRONT[0] + 0.2, lat=FRONT[1], observed_at=ISSUED_AT + timedelta(minutes=minutes))
        for minutes in range(10, 120, 10)
        for _ in range(5)
    ]

    assert forecast(past + future, ISSUED_AT).spread[3].equals(forecast(past, ISSUED_AT).spread[3])


def test_no_forecast_without_enough_recent_and_earlier_hotspots() -> None:
    fire = marching_fire(3, "east")
    only_recent = [h for h in fire if h.observed_at > ISSUED_AT - timedelta(minutes=90)]
    only_earlier = [h for h in fire if h.observed_at <= ISSUED_AT - timedelta(minutes=90)]

    assert forecast([], ISSUED_AT) is None
    assert forecast(only_recent, ISSUED_AT) is None
    assert forecast(only_earlier, ISSUED_AT) is None


def test_a_front_that_has_not_moved_still_grows_evenly() -> None:
    result = forecast(marching_fire(0, "east"), ISSUED_AT)

    assert result is not None
    assert result.heading_deg is None
    assert result.spread[2].area > result.spread[0].area
    assert result.spread[2].contains(result.spread[0])


def test_a_front_that_ran_fast_and_then_went_quiet_keeps_most_of_its_speed() -> None:
    """Satellite coverage thins out and the pixels change; a run at 3 km/h is not forgotten at once."""
    ran = [h for h in marching_fire(3, "east", hours=6) if h.observed_at <= ISSUED_AT - timedelta(minutes=90)]
    # The front stopped 4.5 km behind where it would be now (3 km/h for 90 minutes); detections continue.
    stopped_lon = FRONT[0] - 3 * 1.5 / KM_PER_DEG_LON
    quiet = [
        Hotspot(
            lon=stopped_lon,
            lat=FRONT[1] + across_km / KM_PER_DEG_LAT,
            observed_at=ISSUED_AT - timedelta(minutes=minutes),
        )
        for minutes in range(0, 90, 10)
        for across_km in (-0.6, -0.3, 0.0, 0.3, 0.6)
    ]

    result = forecast(ran + quiet, ISSUED_AT)

    assert result is not None
    assert 2 <= result.speed_kmh <= 3.2
