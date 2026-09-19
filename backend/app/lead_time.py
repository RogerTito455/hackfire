"""Lead time: how long before satellite hotspots came near a zone the system had flagged it.

    lead time = (first hotspot within `radius_km` of the zone) - (first forecast that put the zone in the fire's path)

Both moments come from satellite data alone. A forecast only uses hotspots observed up to its own
issue time (see spread.py), so the flag never sees the future. Nothing here says when the
authorities warned anyone: we do not have that time.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

from shapely import Point
from shapely.ops import transform

from .impact import IssuedForecast, Zone
from .spread import Hotspot, km_per_degree


@dataclass(frozen=True)
class LeadTime:
    flagged_at: datetime
    reached_at: datetime
    minutes: int
    # The hotspot that counted as the fire's arrival, and how far it was from the zone.
    reached_by: Hotspot
    distance_km: float


def lead_time(
    hotspots: Sequence[Hotspot], forecasts: Sequence[IssuedForecast], zone: Zone, radius_km: float
) -> LeadTime | None:
    """None when the zone was never flagged, hotspots never came within the radius, or they did
    before the flag (no advance warning)."""
    flagged_at = min((f.issued_at for f in forecasts if zone.id in f.hours_to_reach), default=None)
    if flagged_at is None:
        return None

    centre = zone.geometry.centroid
    km_per_deg_lon, km_per_deg_lat = km_per_degree(centre.y)
    zone_km = transform(lambda x, y, z=None: (x * km_per_deg_lon, y * km_per_deg_lat), zone.geometry)

    for hotspot in sorted(hotspots, key=lambda h: h.observed_at):
        distance = zone_km.distance(Point(hotspot.lon * km_per_deg_lon, hotspot.lat * km_per_deg_lat))
        if distance <= radius_km:
            if hotspot.observed_at <= flagged_at:
                return None
            minutes = int((hotspot.observed_at - flagged_at).total_seconds() // 60)
            return LeadTime(flagged_at, hotspot.observed_at, minutes, hotspot, distance)
    return None
