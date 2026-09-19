"""Places the fire could reach (data/zones.geojson, from `pnpm data:zones`) and their time to impact."""

import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from functools import cache

from shapely.geometry import shape
from shapely.geometry.base import BaseGeometry

from . import geo, replay, spread
from .config import DATA_DIR

ZONES_FILE = DATA_DIR / "zones.geojson"
# Risk is computed at 15-minute steps, so a replay time and its neighbours share one answer.
STEP = timedelta(minutes=15)


@dataclass(frozen=True)
class Zone:
    id: str
    name: str
    kind: str  # settlement, care_home, school, health
    lat: float
    lon: float
    area_m: BaseGeometry


@cache
def geojson() -> bytes:
    return ZONES_FILE.read_bytes() if ZONES_FILE.exists() else b'{"type":"FeatureCollection","features":[]}'


@cache
def all_zones() -> dict[str, Zone]:
    features = json.loads(geojson())["features"]
    return {
        f["id"]: Zone(
            id=f["id"],
            name=f["properties"]["name"],
            kind=f["properties"]["kind"],
            lat=f["properties"]["lat"],
            lon=f["properties"]["lon"],
            area_m=geo.to_metres(shape(f["geometry"])),
        )
        for f in features
    }


def snap(at: datetime) -> datetime:
    """Round down to STEP."""
    epoch = datetime(1970, 1, 1, tzinfo=at.tzinfo)
    return at - (at - epoch) % STEP


@cache
def minutes_to_impact(zone_id: str, at: datetime) -> int | None:
    zone = all_zones().get(zone_id)
    return None if zone is None else spread.minutes_to_impact(zone.area_m, snap(at))


@cache
def risk(at: datetime) -> list[tuple[Zone, int | None]]:
    """Every zone with its minutes to impact at `at`: reached first, then soonest, then the rest."""
    at = snap(at)
    rows = [(zone, minutes_to_impact(zone.id, at)) for zone in all_zones().values()]
    return sorted(rows, key=lambda row: (row[1] is None, row[1] or 0, row[0].name))


def distance_km(zone_id: str, at: datetime) -> float | None:
    zone = all_zones().get(zone_id)
    return None if zone is None else replay.burned_area_m(snap(at)).distance(zone.area_m) / 1000
