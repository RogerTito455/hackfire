import math
from datetime import UTC, datetime, timedelta

from shapely import box

from app.impact import IssuedForecast, Zone
from app.lead_time import lead_time
from app.spread import Hotspot

LON, LAT = -4.46, 40.38
KM_PER_DEG_LON = 111.32 * math.cos(math.radians(LAT))
# The estate's east edge; hotspots are placed at known distances east of it.
EDGE_LON = LON + 0.005
ESTATE = Zone("estate", "Estate", "estate", box(LON - 0.005, LAT - 0.005, EDGE_LON, LAT + 0.005))

NOON = datetime(2026, 7, 23, 12, 0, tzinfo=UTC)


def at(hours: float) -> datetime:
    return NOON + timedelta(hours=hours)


def hotspot(hours: float, km_from_edge: float) -> Hotspot:
    return Hotspot(lon=EDGE_LON + km_from_edge / KM_PER_DEG_LON, lat=LAT, observed_at=at(hours))


def flagged_from(hours: float) -> list[IssuedForecast]:
    """Forecasts every hour; the estate is in the predicted path from `hours` on."""
    return [
        IssuedForecast(at(h), {"estate": 4} if h >= hours else {}) for h in range(0, 12)
    ]


def test_lead_time_is_the_time_from_the_first_flag_to_the_first_hotspot_within_the_radius() -> None:
    hotspots = [hotspot(1, 12), hotspot(4, 6), hotspot(7, 2.5), hotspot(8, 0.5)]

    result = lead_time(hotspots, flagged_from(1), ESTATE, radius_km=3)

    assert result is not None
    assert result.flagged_at == at(1)
    assert result.reached_at == at(7)
    assert result.minutes == 6 * 60


def test_a_hotspot_just_outside_the_radius_does_not_count_as_arrival() -> None:
    hotspots = [hotspot(5, 3.2), hotspot(6, 2.9)]

    result = lead_time(hotspots, flagged_from(1), ESTATE, radius_km=3)

    assert result is not None
    assert result.reached_at == at(6)
    assert 2.8 <= result.distance_km <= 3.0


def test_hotspots_that_never_come_near_give_no_lead_time() -> None:
    assert lead_time([hotspot(5, 8), hotspot(9, 4)], flagged_from(1), ESTATE, radius_km=3) is None


def test_a_zone_that_was_never_flagged_has_no_lead_time() -> None:
    assert lead_time([hotspot(5, 1)], flagged_from(99), ESTATE, radius_km=3) is None


def test_hotspots_that_arrive_before_the_flag_leave_no_advance_warning() -> None:
    assert lead_time([hotspot(2, 1)], flagged_from(3), ESTATE, radius_km=3) is None
