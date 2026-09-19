"""Predicted fire spread for the replay: a cone from the front's velocity.

Deepfire's simulation cannot start from a past date, so the replay of 23 July estimates how fast
and in which direction the front is moving from the satellite hotspots seen so far, and projects
the current footprint forward hour by hour. See
docs/findings/2026-09-19-deepfire-no-historical-simulation.md.

Only hotspots observed at or before `issued_at` are used: a forecast never sees the future.
"""

import math
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta

from shapely import MultiPoint, Polygon
from shapely.affinity import translate
from shapely.geometry import MultiPolygon
from shapely.ops import transform

KM_PER_DEG_LAT = 110.57
KM_PER_DEG_LON_AT_EQUATOR = 111.32

# The front is measured over the last 3 hours: the recent half against the earlier half.
LOOKBACK = timedelta(hours=3)
MIN_HOTSPOTS_PER_WINDOW = 5
# A satellite pixel is 375 m (VIIRS) or larger; the footprint is padded by the same amount.
PIXEL_KM = 0.4
# A burning front is never assumed slower than this: over-warning beats under-warning, and on
# 23 July a lower floor un-flagged La Atalaya while the front sat 3 km away (satellite gap, stall).
MIN_SPEED_KMH = 1.0
MAX_SPEED_KMH = 6.0
# Spread to the flanks and backwards, as a fraction of the head's speed.
FLANK_FRACTION = 0.3
# The leading edge is the 90th percentile of the hotspots along the heading: robust to strays.
LEADING_EDGE_PERCENTILE = 0.9
# Below this the centroid did not move enough to define a heading.
MIN_HEADING_DISPLACEMENT_KM = 0.1
# One noisy window (thin satellite coverage, a change of sensor) must not erase a run: the speed is
# the strongest estimate of the last 3 hours, taken every 30 minutes, losing 10% per step of age.
PEAK_STEP = timedelta(minutes=30)
PEAK_STEPS = 6
PEAK_DECAY = 0.9


def km_per_degree(lat: float) -> tuple[float, float]:
    """Kilometres per degree of longitude and of latitude at `lat` (equirectangular, fine at 40 km)."""
    return KM_PER_DEG_LON_AT_EQUATOR * math.cos(math.radians(lat)), KM_PER_DEG_LAT


@dataclass(frozen=True)
class Hotspot:
    lon: float
    lat: float
    observed_at: datetime
    # Provenance, for reporting; the model does not use them.
    source: str | None = None
    confidence: str | None = None


@dataclass(frozen=True)
class Forecast:
    issued_at: datetime
    # None when the front did not move enough to define a direction: it then grows evenly.
    heading_deg: float | None
    speed_kmh: float
    # spread[h] is the area predicted burning h hours after issued_at, cumulative and nested.
    # spread[0] is the footprint seen now. Coordinates are (lon, lat).
    spread: list[Polygon | MultiPolygon]


def forecast(
    hotspots: Sequence[Hotspot], issued_at: datetime, horizon_hours: int = 6
) -> Forecast | None:
    """Predict the spread `horizon_hours` ahead, or None when the recent hotspots do not say enough."""
    recent, earlier = _windows(hotspots, issued_at)
    if min(len(recent), len(earlier)) < MIN_HOTSPOTS_PER_WINDOW:
        return None

    lon0 = sum(h.lon for h in recent) / len(recent)
    lat0 = sum(h.lat for h in recent) / len(recent)
    km_per_deg_lon, _ = km_per_degree(lat0)

    def to_km(hotspot: Hotspot) -> tuple[float, float]:
        return ((hotspot.lon - lon0) * km_per_deg_lon, (hotspot.lat - lat0) * KM_PER_DEG_LAT)

    def to_lonlat(x: float, y: float, z: float | None = None) -> tuple[float, float]:
        return (lon0 + x / km_per_deg_lon, lat0 + y / KM_PER_DEG_LAT)

    footprint = MultiPoint([to_km(h) for h in recent]).convex_hull.buffer(PIXEL_KM)
    heading, speed = _strongest_recent_front(hotspots, issued_at, to_km)

    if heading is None:
        polygons = [footprint.buffer(speed * hours) for hours in range(horizon_hours + 1)]
        heading_deg = None
    else:
        ux, uy = heading
        polygons = []
        for hours in range(horizon_hours + 1):
            reach = speed * hours
            sweep = reach * (1 - FLANK_FRACTION)
            swept = MultiPoint(
                [*footprint.exterior.coords, *translate(footprint, ux * sweep, uy * sweep).exterior.coords]
            ).convex_hull
            polygons.append(swept.buffer(reach * FLANK_FRACTION))
        heading_deg = math.degrees(math.atan2(ux, uy)) % 360

    return Forecast(
        issued_at=issued_at,
        heading_deg=heading_deg,
        speed_kmh=speed,
        spread=[transform(to_lonlat, polygon) for polygon in polygons],
    )


def _windows(hotspots: Sequence[Hotspot], at: datetime) -> tuple[list[Hotspot], list[Hotspot]]:
    """The last 3 hours of hotspots split in halves: (recent, earlier). Nothing after `at` is used."""
    seen = [h for h in hotspots if at - LOOKBACK < h.observed_at <= at]
    middle = at - LOOKBACK / 2
    return [h for h in seen if h.observed_at > middle], [h for h in seen if h.observed_at <= middle]


def _front_velocity(
    hotspots: Sequence[Hotspot], at: datetime, to_km: Callable[[Hotspot], tuple[float, float]]
) -> tuple[tuple[float, float] | None, float] | None:
    """Heading (unit vector east, north; None if the front did not move) and speed in km/h at `at`."""
    recent, earlier = _windows(hotspots, at)
    if min(len(recent), len(earlier)) < MIN_HOTSPOTS_PER_WINDOW:
        return None
    recent_km = [to_km(h) for h in recent]
    earlier_km = [to_km(h) for h in earlier]
    heading = _heading(_centroid(earlier_km), _centroid(recent_km))
    if heading is None:
        return None, MIN_SPEED_KMH
    ux, uy = heading
    advance_km = _leading_edge(recent_km, ux, uy) - _leading_edge(earlier_km, ux, uy)
    elapsed_h = (_mean_time(recent) - _mean_time(earlier)).total_seconds() / 3600
    return heading, min(MAX_SPEED_KMH, max(MIN_SPEED_KMH, advance_km / elapsed_h))


def _strongest_recent_front(
    hotspots: Sequence[Hotspot], at: datetime, to_km: Callable[[Hotspot], tuple[float, float]]
) -> tuple[tuple[float, float] | None, float]:
    best = _front_velocity(hotspots, at, to_km) or (None, MIN_SPEED_KMH)
    for steps_ago in range(1, PEAK_STEPS + 1):
        past = _front_velocity(hotspots, at - steps_ago * PEAK_STEP, to_km)
        if past is None or past[0] is None:
            continue
        decayed = past[1] * PEAK_DECAY**steps_ago
        if decayed > best[1]:
            best = (past[0], decayed)
    return best


def _centroid(points: Sequence[tuple[float, float]]) -> tuple[float, float]:
    return (sum(p[0] for p in points) / len(points), sum(p[1] for p in points) / len(points))


def _heading(
    before: tuple[float, float], after: tuple[float, float]
) -> tuple[float, float] | None:
    dx, dy = after[0] - before[0], after[1] - before[1]
    length = math.hypot(dx, dy)
    return None if length < MIN_HEADING_DISPLACEMENT_KM else (dx / length, dy / length)


def _leading_edge(points: Sequence[tuple[float, float]], ux: float, uy: float) -> float:
    along = sorted(p[0] * ux + p[1] * uy for p in points)
    return along[min(len(along) - 1, int(LEADING_EDGE_PERCENTILE * len(along)))]


def _mean_time(hotspots: Sequence[Hotspot]) -> datetime:
    origin = hotspots[0].observed_at
    offsets = sum((h.observed_at - origin for h in hotspots), timedelta()) / len(hotspots)
    return origin + offsets
