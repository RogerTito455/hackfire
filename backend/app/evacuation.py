"""Evacuation and rescue routes that keep away from the fire.

A resident's route goes from their home to the nearest safe point the fire is not heading for, and
avoids the area burned up to the scenario time plus the next AVOID_AHEAD_H of predicted spread
(impact.py, from the cached forecasts). A rescue route goes from the crew base to the resident's
home and avoids only what has burned: crews work inside the fire's path. If even that leaves no way
through, the crew still gets the direct route, with a warning. Routes are cached in memory and in data/routes_cache.json (written by `pnpm data:routes`),
so the live demo does not wait on openrouteservice.
"""

import json
from dataclasses import dataclass
from datetime import datetime
from functools import cache

import httpx
from shapely.geometry import Point, mapping
from shapely.geometry.base import BaseGeometry

from . import geo, impact, replay
from .config import DATA_DIR, settings
from .models import Neighbor, Route, TravelMode
from .providers import routing

PLACES_FILE = DATA_DIR / "places.json"
CACHE_FILE = DATA_DIR / "routes_cache.json"

# ORS takes avoid polygons up to 200 km² and 20 km in height or width: a 14 km square is under both.
AVOID_SQUARE_M = 14_000
# Keep the start and end routable even if the fire area reaches them.
ENDPOINT_CLEARANCE_M = 500
# Residents' routes avoid where the fire is predicted to be within this many hours, too.
AVOID_AHEAD_H = 1
# A safe point must be at least this far from the burned area, and outside the forecast.
SAFE_DISTANCE_M = 3_000
SAFE_POINT_RADIUS_M = 1_000
TIMEOUT_SECONDS = 15


class RoutingUnavailable(Exception):
    """openrouteservice failed (quota, outage, timeout) and the route is not cached."""


@dataclass(frozen=True)
class Place:
    id: str
    name: str
    lat: float
    lon: float


@cache
def _places() -> tuple[list[Place], Place]:
    raw = json.loads(PLACES_FILE.read_text(encoding="utf-8"))
    safe = [Place(p["id"], p["name"], p["lat"], p["lon"]) for p in raw["safe_points"]]
    base = raw["crew_base"]
    return safe, Place(base["id"], base["name"], base["lat"], base["lon"])


def crew_base() -> Place:
    return _places()[1]


def fire_m(at: datetime, ahead_h: float) -> BaseGeometry:
    """The area burned by `at` plus, if `ahead_h`, where the forecast puts the fire by then (metres)."""
    burned = replay.burned_area_m(at)
    footprint = impact.predicted_footprint(at, ahead_h) if ahead_h > 0 else None
    return burned if footprint is None else burned.union(geo.to_metres(footprint))


def _is_safe(place: Place, at: datetime) -> bool:
    area = geo.point_m(place.lon, place.lat).buffer(SAFE_POINT_RADIUS_M)
    return replay.burned_area_m(at).distance(area) >= SAFE_DISTANCE_M and not fire_m(
        at, impact.HORIZON_HOURS
    ).intersects(area)


def safest_point(at: datetime, start: tuple[float, float] | None = None) -> Place:
    """The nearest safe point the forecast does not reach and that is clear of the fire.

    Nearest to `start` as the crow flies. If none qualifies, the one farthest from the fire.
    """
    candidates = [p for p in _places()[0] if _is_safe(p, at)]
    if not candidates:
        burned = replay.burned_area_m(at)
        return max(_places()[0], key=lambda p: burned.distance(geo.point_m(p.lon, p.lat)))
    if start is None:
        return candidates[0]
    here = geo.point_m(*start)
    return min(candidates, key=lambda p: here.distance(geo.point_m(p.lon, p.lat)))


def avoid_polygon(
    start: tuple[float, float], end: tuple[float, float], at: datetime, ahead_h: float = AVOID_AHEAD_H
) -> dict | None:
    """The fire area around this route, clipped to what ORS accepts, as GeoJSON in lon/lat."""
    a, b = geo.point_m(*start), geo.point_m(*end)
    middle = Point((a.x + b.x) / 2, (a.y + b.y) / 2)
    area = (
        fire_m(at, ahead_h)
        .intersection(geo.square_m(middle, AVOID_SQUARE_M))
        .difference(a.buffer(ENDPOINT_CLEARANCE_M))
        .difference(b.buffer(ENDPOINT_CLEARANCE_M))
    )
    return None if area.is_empty else mapping(geo.to_degrees(area))


# --- Spoken directions ---------------------------------------------------------


def _distance_phrase(metres: float) -> str:
    if metres < 1000:
        return f"about {round(metres, -2):.0f} metres"
    return f"about {round(metres / 1000):.0f} kilometres"


def _duration_phrase(seconds: float, how: str) -> str:
    minutes = max(1, round(seconds / 60))
    if minutes < 60:
        return f"around {minutes} minutes {how}"
    hours, rest = divmod(round(minutes / 10) * 10, 60)
    unit = "hour" if hours == 1 else "hours"
    return f"around {hours} {unit} {how}" if rest == 0 else f"around {hours} {unit} and {rest} minutes {how}"


def _main_roads(steps: list[dict], limit: int = 3) -> list[str]:
    """The longest named roads on the route, in the order they are driven."""
    stretches: list[list] = []
    for step in steps:
        name = (step.get("name") or "").strip()
        if name in ("", "-"):
            continue
        if stretches and stretches[-1][0] == name:
            stretches[-1][1] += step["distance"]
        else:
            stretches.append([name, step["distance"]])
    longest = sorted(range(len(stretches)), key=lambda i: -stretches[i][1])[:limit]
    return [stretches[i][0] for i in sorted(longest) if stretches[i][1] >= 300]


def spoken_directions(feature: dict, mode: TravelMode, destination: str, avoided_fire: bool, ahead_h: float = 0) -> str:
    """Two or three sentences a person can follow on a phone call."""
    summary = feature["properties"]["summary"]
    steps = [step for segment in feature["properties"]["segments"] for step in segment["steps"]]
    roads = _main_roads(steps)
    verb = "Drive" if mode == TravelMode.CAR else "Walk"
    way = f" along {', then '.join(roads)}" if roads else ""
    how = "by car" if mode == TravelMode.CAR else "on foot"
    text = (
        f"{verb} to {destination}{way}. "
        f"It is {_distance_phrase(summary.get('distance', 0))}, {_duration_phrase(summary.get('duration', 0), how)}."
    )
    if not avoided_fire:
        return text
    if ahead_h > 0:
        return text + " This route keeps away from the fire and from where it is expected to spread in the next hour."
    return text + " This route keeps away from the area the fire has already burned."


# --- Planning and cache --------------------------------------------------------

_memory: dict[str, dict] = {}


@cache
def _disk_cache() -> dict[str, dict]:
    return json.loads(CACHE_FILE.read_text(encoding="utf-8")) if CACHE_FILE.exists() else {}


def cache_key(
    start: tuple[float, float], end: tuple[float, float], mode: TravelMode, at: datetime, ahead_h: float
) -> str:
    return f"{mode}:{start[0]:.5f},{start[1]:.5f}->{end[0]:.5f},{end[1]:.5f}@{at.isoformat()}+{ahead_h:g}h"


def plan(
    start: tuple[float, float],
    end: tuple[float, float],
    mode: TravelMode,
    destination: str,
    at: datetime,
    refresh: bool = False,
    ahead_h: float = AVOID_AHEAD_H,
    crew: bool = False,
) -> Route:
    """A route from the cache, or from openrouteservice. `refresh` skips both caches.

    For a crew, a blocked route falls back to the direct one, with a warning first.
    """
    key = cache_key(start, end, mode, at, ahead_h)
    cached = None if refresh else _memory.get(key) or _disk_cache().get(key)
    if cached is not None:
        _memory[key] = cached
        return Route(**cached)
    avoid = avoid_polygon(start, end, at, ahead_h)
    warning = ""
    try:
        with httpx.Client(timeout=TIMEOUT_SECONDS) as client:
            try:
                feature = routing.route_avoiding(client, start, end, mode, avoid)
            except routing.NoRouteFound:
                if not crew:
                    raise
                feature = routing.route_avoiding(client, start, end, mode, None)
                avoid, warning = None, "Warning: no route avoids the burned area. "
    except routing.NoRouteFound:
        route = Route(
            mode=mode,
            spoken_directions=(
                "No route that keeps away from the fire was found. "
                "Follow the instructions of the emergency services on site."
            ),
        )
    except httpx.HTTPError as error:
        raise RoutingUnavailable(str(error)) from error
    else:
        summary = feature["properties"]["summary"]
        route = Route(
            mode=mode,
            distance_m=summary.get("distance"),
            duration_s=summary.get("duration"),
            spoken_directions=warning
            + spoken_directions(feature, mode, destination, avoided_fire=avoid is not None, ahead_h=ahead_h),
            geometry=feature["geometry"],
        )
    _memory[key] = route.model_dump(mode="json")
    return route


def evacuation_route(
    neighbor: Neighbor, mode: TravelMode, at: datetime | None = None, refresh: bool = False
) -> Route:
    at = at or settings.scenario_time
    target = safest_point(at, (neighbor.lon, neighbor.lat))
    return plan((neighbor.lon, neighbor.lat), (target.lon, target.lat), mode, target.name, at, refresh)


def rescue_route(neighbor: Neighbor, at: datetime | None = None, refresh: bool = False) -> Route:
    at = at or settings.scenario_time
    base = crew_base()
    start, end = (base.lon, base.lat), (neighbor.lon, neighbor.lat)
    return plan(start, end, TravelMode.CAR, neighbor.address, at, refresh, ahead_h=0, crew=True)


def fire_area(at: datetime | None = None, crew: bool = False) -> dict:
    """The area routes avoid, as a GeoJSON Feature: residents' routes, or with `crew`, crews'."""
    at = at or settings.scenario_time
    ahead_h = 0 if crew else AVOID_AHEAD_H
    return {
        "type": "Feature",
        "geometry": mapping(geo.to_degrees(fire_m(at, ahead_h))),
        "properties": {"until": at.isoformat(), "ahead_hours": ahead_h},
    }


def export_cache() -> dict[str, dict]:
    """Everything planned in this process, for `pnpm data:routes`."""
    return dict(sorted(_memory.items()))
