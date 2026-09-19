"""Live operations for one real fire: the places its Deepfire ELMFIRE run reaches, when, and drafts.

For the live fire the coordinator selects, and only that one:

1. Places at risk: OpenStreetMap towns, villages, housing estates, care homes, schools, health
   centres and main roads inside the run's 12 h footprint plus BUFFER_M. Overpass is asked once per
   simulation id (a completed run never changes); the answer is kept in memory and under CACHE_DIR,
   so a second click is instant and an Overpass outage shows the last result for that fire.
2. Time to impact: from the run's hourly cumulative polygons, the first hour that touches each place
   (impact.first_hour_touching), counted from when Deepfire ran it.
3. Alert drafts for the coordinator, soonest first. Nothing is ever sent: there is no public
   alerting channel here (ES-Alert and SMS to zones are future work).
4. Roads to close: those the run reaches within ROAD_CLOSED_WITHIN_MIN of now, the replay's rule
   (frontend/src/domain/zones.ts, closedRoads): closed to residents, crews still use them.

A prediction, not an official warning. Nothing here queues a Deepfire simulation.
"""

import json
import math
import re
import threading
import time
from datetime import UTC, datetime, timedelta

import httpx
import shapely
from shapely import affinity
from shapely.geometry import Point, shape
from shapely.ops import unary_union

from . import i18n, live_dgt, live_spread
from .config import DATA_DIR
from .impact import first_hour_touching
from .pipelines import fetch_zones
from .providers import overpass

CACHE_DIR = DATA_DIR / "live_places"
# Places this close to the 12 h footprint are listed too, as near it but not reached.
BUFFER_M = 1000
# The replay's rule: a road the fire reaches within the hour is closed to residents.
ROAD_CLOSED_WITHIN_MIN = 60
# Overpass: seconds per request; no further mirror is tried after DEADLINE_SECONDS; the tile size.
TIMEOUT_SECONDS = 20
DEADLINE_SECONDS = 30
TILE_DEG = 0.3
MAX_TILES = 9

# OSM place nodes are points: pad them to roughly the size of the settlement.
PLACE_RADIUS_M = {"city": 2000, "town": 900, "village": 400, "hamlet": 150, "suburb": 500, "quarter": 300, "neighbourhood": 250}
PLACE_KIND = {
    "city": "town",
    "town": "town",
    "village": "town",
    "hamlet": "town",
    "suburb": "estate",
    "quarter": "estate",
    "neighbourhood": "estate",
}
# Who is hurt most comes first among places the fire reaches at the same time (as domain/zones.ts).
KIND_PRIORITY = ["estate", "town", "care_home", "health_centre", "school", "road"]

_M_PER_DEG = 111_320.0


class NoSimulation(Exception):
    """The fire has no completed Deepfire run to read places at risk from."""


class PlacesUnavailable(Exception):
    """Overpass failed and nothing is cached for this fire."""


# --- Geometry, pure ------------------------------------------------------------------------------


def _scale(geometry, lat0: float, inverse: bool = False):
    x, y = _M_PER_DEG * math.cos(math.radians(lat0)), _M_PER_DEG
    if inverse:
        x, y = 1 / x, 1 / y
    return affinity.scale(geometry, xfact=x, yfact=y, origin=(0, 0))


def buffer_m(geometry, metres: float, lat0: float | None = None):
    """`geometry` (lon/lat) grown by `metres`, measured at its own latitude."""
    lat0 = geometry.centroid.y if lat0 is None else lat0
    return _scale(_scale(geometry, lat0).buffer(metres, quad_segs=4), lat0, inverse=True)


def hourly_polygons(hours: list[dict]) -> dict[int, object]:
    """A run's hours as served by live_spread: {hour: shapely geometry}."""
    return {hour["hour"]: shape(hour["geometry"]) for hour in hours}


def search_area(hourly: dict[int, object], metres: float = BUFFER_M):
    """The run's whole footprint (the hours are cumulative, but take their union anyway) plus a buffer."""
    return buffer_m(unary_union(list(hourly.values())), metres)


def tiles(bounds: tuple[float, float, float, float], size: float = TILE_DEG) -> list[tuple[float, float, float, float]]:
    """The box cut into tiles of at most `size` degrees a side, so one Overpass query stays small."""
    west, south, east, north = bounds
    columns = max(1, math.ceil((east - west) / size))
    rows = max(1, math.ceil((north - south) / size))
    width, height = (east - west) / columns, (north - south) / rows
    return [
        (west + c * width, south + r * height, west + (c + 1) * width, south + (r + 1) * height)
        for r in range(rows)
        for c in range(columns)
    ]


# --- Places from OpenStreetMap -------------------------------------------------------------------


def places_query(bbox: str) -> str:
    """Settlements, named housing estates, and fetch_zones' facilities and main roads, in one query."""
    return f"""
[out:json][timeout:{TIMEOUT_SECONDS}];
(
  node["place"~"^({"|".join(PLACE_KIND)})$"]({bbox});
  way["landuse"="residential"]["name"]({bbox});{fetch_zones.facility_statements(bbox)}
  {fetch_zones.road_statement(bbox)}
);
out geom tags;
"""


def _with_center(element: dict) -> dict:
    """`out geom` gives ways their outline but no centre, and relations only their bounds."""
    if "lon" in element or "center" in element or not (bounds := element.get("bounds")):
        return element
    center = {"lat": (bounds["minlat"] + bounds["maxlat"]) / 2, "lon": (bounds["minlon"] + bounds["maxlon"]) / 2}
    return {**element, "center": center}


def _feature(zone_id: str, name: str | None, kind: str, osm: str | None, geometry) -> dict:
    return fetch_zones.feature(zone_id, name, kind, osm, shapely.set_precision(geometry, fetch_zones.COORDINATE_GRID_DEG))


def parse_places(elements: list[dict], area) -> list[dict]:
    """The places among Overpass `elements` that touch `area`, as zone features (fetch_zones' shape).

    Place nodes are padded to their settlement's size; housing estates are named residential land use,
    merged by name and dropped when a town of the same name is listed; roads are grouped by number and
    clipped to `area`. Pure.
    """
    features: dict[str, dict] = {}
    estates: dict[str, list] = {}
    roads: list[dict] = []
    for element in elements:
        tags = element.get("tags") or {}
        ident = f"{element['type'][0]}{element['id']}"
        osm = f"{element['type']}/{element['id']}"
        if "highway" in tags:
            roads.append(element)
            continue
        if element["type"] == "node" and tags.get("place") in PLACE_KIND:
            kind = PLACE_KIND[tags["place"]]
            geometry = buffer_m(Point(element["lon"], element["lat"]), PLACE_RADIUS_M[tags["place"]])
        elif tags.get("landuse") == "residential":
            if (polygon := fetch_zones.way_polygon(element)) is not None and polygon.intersects(area):
                estates.setdefault(tags["name"], []).append(polygon)
            continue
        elif (kind := fetch_zones.facility_kind(tags)) is not None:
            geometry = fetch_zones.facility_geometry(_with_center(element))
        else:
            continue
        if geometry is None or geometry.is_empty or not geometry.intersects(area):
            continue
        zone_id = f"{kind.replace('_', '-')}-{ident}"
        features[zone_id] = _feature(zone_id, tags.get("name"), kind, osm, geometry)

    towns = {f["properties"]["name"] for f in features.values() if f["properties"]["kind"] == "town"}
    for name, polygons in estates.items():
        if name not in towns:
            slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "unnamed"
            features[f"estate-{slug}"] = _feature(f"estate-{slug}", name, "estate", None, unary_union(polygons))

    for ref, lines in fetch_zones.roads_by_ref(roads).items():
        geometry = fetch_zones.finish(lines, simplify=fetch_zones.ROAD_TOLERANCE_DEG, box=area)
        if geometry is not None and not geometry.is_empty:
            features[fetch_zones.road_id(ref)] = fetch_zones.feature(fetch_zones.road_id(ref), ref, "road", None, geometry)
    # Plain JSON (lists, not shapely's tuples), as it comes back from the cache file.
    return json.loads(json.dumps(list(features.values())))


def _fetch_elements(area) -> list[dict]:
    """Overpass, tile by tile, each element once. Any failure fails the lot."""
    boxes = tiles(area.bounds)
    if len(boxes) > MAX_TILES:
        raise PlacesUnavailable(f"footprint too large for one fetch ({len(boxes)} tiles)")
    found: dict[tuple[str, int], dict] = {}
    deadline = time.monotonic() + DEADLINE_SECONDS
    with httpx.Client(timeout=TIMEOUT_SECONDS + 5) as client:
        for box in boxes:
            query = places_query(fetch_zones.overpass_bbox(box))
            for element in overpass.elements(client, query, deadline=deadline):
                found[(element["type"], element["id"])] = element
    return list(found.values())


# --- Cache per simulation id ---------------------------------------------------------------------

_places: dict[str, dict] = {}
_locks: dict[str, threading.Lock] = {}
_guard = threading.Lock()


def _file(simulation_id: str):
    return CACHE_DIR / f"{re.sub(r'[^A-Za-z0-9_-]', '_', simulation_id)}.json"


def _read(path) -> dict | None:
    try:
        body = json.loads(path.read_text(encoding="utf-8"))
        return body if isinstance(body.get("features"), list) else None
    except (OSError, ValueError, AttributeError):
        return None


def _write(entry: dict) -> None:
    """Best effort: a read-only disk only loses the fallback."""
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        path = _file(entry["simulation_id"])
        temporary = path.with_suffix(".tmp")
        temporary.write_text(json.dumps(entry, separators=(",", ":")), encoding="utf-8")
        temporary.replace(path)
    except OSError:
        pass


def _last_for_fire(fire_id: str) -> dict | None:
    """The newest cached places of any run of this fire, from memory or disk."""
    candidates = [entry for entry in _places.values() if entry["fire_id"] == fire_id]
    if CACHE_DIR.exists():
        candidates += [entry for path in CACHE_DIR.glob("*.json") if (entry := _read(path)) and entry.get("fire_id") == fire_id]
    return max(candidates, key=lambda entry: entry["fetched_at"], default=None)


def places_for(simulation_id: str, fire_id: str, hourly: dict[int, object]) -> tuple[dict, bool]:
    """The places at risk for one run, and whether they are stale (from an earlier run of the fire).

    Memory, then disk, then Overpass. If Overpass fails, the fire's last cached places come back
    stale; with none, raises PlacesUnavailable.
    """
    with _guard:
        lock = _locks.setdefault(simulation_id, threading.Lock())
    with lock:  # two clicks on the same fire ask Overpass once
        if (entry := _places.get(simulation_id)) is not None:
            return entry, False
        if (entry := _read(_file(simulation_id))) is not None:
            _places[simulation_id] = entry
            return entry, False
        area = search_area(hourly)
        try:
            features = parse_places(_fetch_elements(area), area)
        except (httpx.HTTPError, KeyError, ValueError, PlacesUnavailable) as error:
            if (fallback := _last_for_fire(fire_id)) is not None:
                return fallback, True
            raise PlacesUnavailable(str(error)) from error
        entry = {
            "simulation_id": simulation_id,
            "fire_id": fire_id,
            "fetched_at": datetime.now(UTC).isoformat(),
            "buffer_m": BUFFER_M,
            "features": features,
        }
        _places[simulation_id] = entry
        _write(entry)
        return entry, False


def reset_cache() -> None:
    _places.clear()
    _locks.clear()


# --- Time to impact, roads and drafts, pure ------------------------------------------------------


def _iso(moment: datetime) -> str:
    return moment.astimezone(UTC).isoformat().replace("+00:00", "Z")


def assess(features: list[dict], hourly: dict[int, object], run_at: datetime, now: datetime) -> list[dict]:
    """Each place with its time to impact, soonest first; places the run never reaches come last.

    `minutes_from_run`: from the run's start to the first hour whose polygon touches the place.
    `minutes`: what is left of that at `now`, 0 when it is due or past. Both None when not reached.
    """
    age_minutes = (now - run_at).total_seconds() / 60
    places = []
    for feature in features:
        properties = feature["properties"]
        hour = first_hour_touching(hourly, shape(feature["geometry"]))
        from_run = None if hour is None else hour * 60
        places.append(
            {
                **properties,
                "geometry": feature["geometry"],
                "hour": hour,
                "minutes_from_run": from_run,
                "reaches_at": None if hour is None else _iso(run_at + timedelta(hours=hour)),
                "minutes": None if from_run is None else max(0, round(from_run - age_minutes)),
            }
        )
    return sorted(places, key=_order)


def _order(place: dict) -> tuple:
    reached = place["minutes_from_run"] is not None
    return (
        not reached,
        place["minutes_from_run"] if reached else 0,
        KIND_PRIORITY.index(place["kind"]) if place["kind"] in KIND_PRIORITY else len(KIND_PRIORITY),
        place["name"] or "",
        place["id"],
    )


def roads_to_close(places: list[dict], within: int = ROAD_CLOSED_WITHIN_MIN) -> list[str]:
    """Roads the run reaches within `within` minutes of now: closed to residents, crews still use them."""
    return [p["id"] for p in places if p["kind"] == "road" and p["minutes"] is not None and p["minutes"] <= within]


def alert_drafts(places: list[dict], locale: str | None = None) -> list[dict]:
    """One draft per reached place other than roads, soonest first, in `locale` (default: the request's).

    Drafts for the coordinator to review. Nothing sends them.
    """
    drafts = []
    for place in places:
        if place["kind"] == "road" or place["minutes"] is None:
            continue
        name = place["name"] or i18n.t(f"liveOps.unnamed.{place['kind']}", locale)
        minutes = place["minutes"]
        if minutes <= 0:
            text = i18n.t("liveOps.alertDue", locale, place=name)
        elif minutes < 60:
            text = i18n.t("liveOps.alertSoon", locale, place=name)
        else:
            text = i18n.t("liveOps.alert", locale, place=name, count=math.floor(minutes / 60 + 0.5))
        drafts.append({"zone_id": place["id"], "place": name, "minutes": minutes, "text": text, "draft": True, "sent": False})
    return drafts


# --- The endpoint's answer -----------------------------------------------------------------------


def _parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def operations(fire_id: str, now: datetime | None = None) -> dict:
    """Places at risk, their time to impact, alert drafts and roads to close for one live fire, and
    the DGT's official incidents and closures near it (never fails for the DGT's sake).

    Raises live.LiveUnavailable (Deepfire down, nothing cached), NoSimulation or PlacesUnavailable.
    """
    spread = live_spread.predicted_spread()
    run = next((fire for fire in spread["fires"] if fire["fire_id"] == fire_id), None)
    if run is None:
        raise NoSimulation(fire_id)
    hourly = hourly_polygons(run["hours"])
    entry, places_stale = places_for(run["simulation_id"], fire_id, hourly)
    now = now or datetime.now(UTC)
    run_at = _parse_time(run["created_at"])
    places = assess(entry["features"], hourly, run_at, now)
    return {
        "fire_id": fire_id,
        "simulation_id": run["simulation_id"],
        "name": run["name"],
        "location": run.get("location"),
        "run_at": run["created_at"],
        "model": run["model"],
        "duration_hours": run.get("duration_hours"),
        "buffer_m": entry.get("buffer_m", BUFFER_M),
        "road_closed_within_minutes": ROAD_CLOSED_WITHIN_MIN,
        "places": places,
        "alerts": alert_drafts(places),
        "roads_to_close": roads_to_close(places),
        "places_fetched_at": entry["fetched_at"],
        # Official DGT forest-fire incidents and closures within the footprint plus live_dgt.NEAR_FIRE_M.
        "dgt": live_dgt.near_area(search_area(hourly, live_dgt.NEAR_FIRE_M)),
        # Places from an earlier run of this fire, because Overpass failed for this one.
        "places_stale": places_stale,
        "spread_stale": spread["stale"],
        "computed_at": _iso(now),
    }
