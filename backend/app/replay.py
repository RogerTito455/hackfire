"""Cached fire data for the replay of 22–24 July 2026, read from data/ and served as-is."""

from functools import cache

from .config import DATA_DIR

HOTSPOTS_FILE = DATA_DIR / "hotspots_2026-07-22_24.geojson"


@cache
def hotspots_geojson() -> bytes | None:
    """The hotspot FeatureCollection written by `pnpm data:hotspots`, or None if it is missing.

    Served as raw bytes: re-encoding ~7,000 features on every request would cost more than the
    request itself.
    """
    return HOTSPOTS_FILE.read_bytes() if HOTSPOTS_FILE.exists() else None
