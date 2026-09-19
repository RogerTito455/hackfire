"""Cached fire data for the replay of 22–24 July 2026, read from data/ and served as-is."""

from functools import cache

from shapely import box

from .config import DATA_DIR

HOTSPOTS_FILE = DATA_DIR / "hotspots_2026-07-22_24.geojson"
# Demo box around Burgohondo, El Tiemblo and La Atalaya (min lon, min lat, max lon, max lat).
# Every cached polygon is clipped to it.
DEMO_BOX = box(-4.85, 40.30, -4.40, 40.50)
SPREAD_FILE = DATA_DIR / "spread_2026-07-23.geojson"
ZONES_FILE = DATA_DIR / "zones.geojson"
LEAD_TIME_FILE = DATA_DIR / "lead_time_la-atalaya.json"


@cache
def hotspots_geojson() -> bytes | None:
    """The hotspot FeatureCollection written by `pnpm data:hotspots`, or None if it is missing.

    Served as raw bytes: re-encoding ~7,000 features on every request would cost more than the
    request itself.
    """
    return HOTSPOTS_FILE.read_bytes() if HOTSPOTS_FILE.exists() else None


@cache
def spread_geojson() -> bytes | None:
    """The predicted spread written by `pnpm data:spread`, or None if it is missing."""
    return SPREAD_FILE.read_bytes() if SPREAD_FILE.exists() else None


@cache
def zones_geojson() -> bytes | None:
    """The zones written by `pnpm data:zones`, or None if it is missing."""
    return ZONES_FILE.read_bytes() if ZONES_FILE.exists() else None


@cache
def lead_time_json() -> bytes | None:
    """The lead time written by `pnpm data:lead-time`, or None if it is missing."""
    return LEAD_TIME_FILE.read_bytes() if LEAD_TIME_FILE.exists() else None

