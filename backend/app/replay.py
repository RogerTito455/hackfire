"""Cached fire data for the replay of 22–24 July 2026, read from data/."""

import json
from datetime import datetime
from functools import cache

import shapely
from shapely.geometry.base import BaseGeometry

from . import geo
from .config import DATA_DIR

HOTSPOTS_FILE = DATA_DIR / "hotspots_2026-07-22_24.geojson"


@cache
def hotspots_geojson() -> bytes | None:
    """The hotspot FeatureCollection written by `pnpm data:hotspots`, or None if it is missing.

    Served as raw bytes: re-encoding ~7,000 features on every request would cost more than the
    request itself.
    """
    return HOTSPOTS_FILE.read_bytes() if HOTSPOTS_FILE.exists() else None


# Satellite pixels are 375 m (VIIRS) to about 2 km (MTG): a hotspot stands for an area, not a point.
HOTSPOT_RADIUS_M = 750


@cache
def _hotspot_times_and_points() -> tuple[list[datetime], list[tuple[float, float]]]:
    body = hotspots_geojson()
    features = json.loads(body)["features"] if body else []
    times = [datetime.fromisoformat(f["properties"]["observed_at"]) for f in features]
    points = [tuple(f["geometry"]["coordinates"][:2]) for f in features]
    return times, points


@cache
def burned_area_m(until: datetime) -> BaseGeometry:
    """The area the fire had reached by `until`, in local metres (see geo.py).

    Every hotspot observed so far, buffered by HOTSPOT_RADIUS_M and merged, then simplified
    to 100 m so it stays small enough to send to openrouteservice.
    """
    times, points = _hotspot_times_and_points()
    seen = [geo.point_m(lon, lat) for (lon, lat), t in zip(points, times, strict=True) if t <= until]
    # One buffer per hotspot, then a tree union: buffering the MultiPoint in one pass peaked at
    # ~1.9 GB and 17 s, enough for Railway to kill the process.
    return shapely.union_all(shapely.buffer(seen, HOTSPOT_RADIUS_M)).simplify(100)
