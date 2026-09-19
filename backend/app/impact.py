"""Which zones the predicted spread reaches, and when. Reads the cached spread and zones in data/.

A forecast issued at time T says, for each zone, in how many hours the spread first touches it.
Between two forecasts the last one stays valid for MAX_FORECAST_AGE and its minutes count down, so
a gap in the satellite data does not un-flag a zone. Everything the dashboard shows and everything
`get_fire_status` says comes from `minutes_to_impact`.
"""

import json
from bisect import bisect_right
from dataclasses import dataclass
from datetime import datetime, timedelta
from functools import cache

from shapely.geometry import shape

from .replay import SPREAD_FILE, ZONES_FILE

MAX_FORECAST_AGE = timedelta(hours=3)
# How far ahead each forecast looks; the same horizon build_spread.py writes.
HORIZON_HOURS = 6


@dataclass(frozen=True)
class Zone:
    id: str
    name: str | None
    kind: str
    geometry: object


@dataclass(frozen=True)
class IssuedForecast:
    issued_at: datetime
    # Zone id -> first hour ahead (0 is the fire as seen now) whose polygon touches the zone.
    # Zones the spread never reaches are absent.
    hours_to_reach: dict[str, int]


@cache
def zones() -> dict[str, Zone]:
    if not ZONES_FILE.exists():
        return {}
    collection = json.loads(ZONES_FILE.read_text(encoding="utf-8"))
    return {
        f["id"]: Zone(f["id"], f["properties"]["name"], f["properties"]["kind"], shape(f["geometry"]))
        for f in collection["features"]
    }


@cache
def forecasts() -> list[IssuedForecast]:
    """Cached forecasts sorted by issue time, with each zone's hours to reach precomputed."""
    if not SPREAD_FILE.exists():
        return []
    polygons: dict[datetime, dict[int, object]] = {}
    for feature in json.loads(SPREAD_FILE.read_text(encoding="utf-8"))["features"]:
        properties = feature["properties"]
        issued_at = datetime.fromisoformat(properties["issued_at"])
        polygons.setdefault(issued_at, {})[properties["hour"]] = shape(feature["geometry"])

    issued = []
    for issued_at in sorted(polygons):
        hourly = polygons[issued_at]
        hours_to_reach = {}
        for zone in zones().values():
            hour = next((h for h in sorted(hourly) if hourly[h].intersects(zone.geometry)), None)
            if hour is not None:
                hours_to_reach[zone.id] = hour
        issued.append(IssuedForecast(issued_at, hours_to_reach))
    return issued


@cache
def _issue_times() -> list[datetime]:
    return [f.issued_at for f in forecasts()]


def forecast_at(at: datetime) -> IssuedForecast | None:
    """The latest forecast issued at or before `at`, unless it is older than MAX_FORECAST_AGE."""
    issued = forecasts()
    index = bisect_right(_issue_times(), at) - 1
    if index < 0 or at - issued[index].issued_at > MAX_FORECAST_AGE:
        return None
    return issued[index]


def minutes_to_impact(zone_id: str, at: datetime) -> int | None:
    """Minutes until the predicted fire reaches the zone; 0 if it is there already, None if never."""
    forecast = forecast_at(at)
    if forecast is None or zone_id not in forecast.hours_to_reach:
        return None
    age_minutes = (at - forecast.issued_at).total_seconds() / 60
    return max(0, round(forecast.hours_to_reach[zone_id] * 60 - age_minutes))


def remaining_horizon_minutes(at: datetime) -> int | None:
    """How far ahead the forecast in force at `at` still looks, or None when there is none."""
    forecast = forecast_at(at)
    if forecast is None:
        return None
    age_minutes = (at - forecast.issued_at).total_seconds() / 60
    return max(0, int(HORIZON_HOURS * 60 - age_minutes))


def zone_name(zone_id: str) -> str:
    zone = zones().get(zone_id)
    return zone.name if zone and zone.name else zone_id


def timeline(step: timedelta = timedelta(minutes=5)) -> dict | None:
    """Forecast in force and minutes to impact at every `step`, for the dashboard to look up.

    Only zones that are ever at risk are listed. None when there are no cached forecasts.
    """
    issued = forecasts()
    if not issued:
        return None
    start, end = issued[0].issued_at, issued[-1].issued_at + MAX_FORECAST_AGE
    moments = [start + step * i for i in range(int((end - start) / step) + 1)]
    in_force = [forecast_at(moment) for moment in moments]
    at_risk = sorted({zone for f in issued for zone in f.hours_to_reach})
    return {
        "start": start.isoformat().replace("+00:00", "Z"),
        "step_minutes": int(step.total_seconds() // 60),
        "forecast": [f.issued_at.isoformat().replace("+00:00", "Z") if f else None for f in in_force],
        "zones": {zone: [minutes_to_impact(zone, m) for m in moments] for zone in at_risk},
    }
