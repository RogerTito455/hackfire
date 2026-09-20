"""Live mode's predicted spread: the ELMFIRE runs Deepfire makes on its own on the fires burning now.

Deepfire simulates active fires automatically (`auto: true`: terrain, fuel and weather). We only read
those runs, never queue one. Each active fire the dashboard shows gets the latest `COMPLETED` run
whose ignition point lies within MATCH_KM of it: list items have no cluster id, and their `fireId`
names a reported fire, not a cluster.

The answer is cached in memory for CACHE_SECONDS and the last good one is written to CACHE_FILE, so
a Deepfire outage (503 under load) or a restart still shows the last result, marked `stale: true`.
"""

import json
import math
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import httpx

from . import live
from .config import DATA_DIR
from .providers import deepfire

CACHE_FILE = DATA_DIR / "live_spread.json"
CACHE_SECONDS = 300
# After a failure, the stale answer is served this long before Deepfire is asked again.
RETRY_SECONDS = 60
LOOKBACK_HOURS = 24
# About 125 runs a day over Spain on 2026-09-19: two pages of 100.
MAX_PAGES = 3
MATCH_KM = 3.0
TIMEOUT_SECONDS = 15
DETAIL_WORKERS = 6


@dataclass
class _Snapshot:
    fires: list[dict]
    fetched_at: datetime
    # When to ask Deepfire again (time.monotonic()).
    expires: float
    stale: bool = False


# Norma global keyword used inside a function: Deepfire's last completed run per fire, rebound under
# `_lock` by `predicted_spread` and cleared by `reset_cache`. A module-level cache.
_snapshot: _Snapshot | None = None
# A completed run never changes: its hourly polygons and burned area, by simulation id. Seeded from
# CACHE_FILE after a restart, so only runs that are new since then are fetched.
_runs: dict[str, dict] = {}
_lock = threading.Lock()


def _fetch_simulations(since: datetime) -> list[dict]:
    with httpx.Client(timeout=TIMEOUT_SECONDS) as client:
        return deepfire.simulations_since(client, deepfire.cached_token(client), since, MAX_PAGES)


def _fetch_details(simulation_ids: list[str]) -> dict[str, dict]:
    """Each simulation in full, a few at a time. Any failure fails them all."""
    if not simulation_ids:
        return {}
    with httpx.Client(timeout=TIMEOUT_SECONDS) as client:
        token = deepfire.cached_token(client)
        with ThreadPoolExecutor(DETAIL_WORKERS) as pool:
            bodies = pool.map(lambda sim_id: deepfire.simulation(client, token, sim_id), simulation_ids)
            return dict(zip(simulation_ids, bodies, strict=True))


def _km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dlat, dlon = p2 - p1, math.radians(lon2 - lon1)
    h = math.sin(dlat / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlon / 2) ** 2
    return 2 * 6371.0 * math.asin(math.sqrt(h))


def match_runs(simulations: list[dict], fires: list[dict], max_km: float = MATCH_KM) -> dict[str, dict]:
    """The latest COMPLETED run per active fire, as {cluster id: list item}.

    A run belongs to the nearest fire within `max_km` of its ignition point. Pure, for the tests.
    """
    points = [
        (fire["properties"]["id"], fire["geometry"]["coordinates"][1], fire["geometry"]["coordinates"][0])
        for fire in fires
    ]
    matched: dict[str, dict] = {}
    completed = [sim for sim in simulations if sim.get("status") == "COMPLETED"]
    for sim in sorted(completed, key=lambda sim: sim["createdAt"], reverse=True):
        lat, lon = sim.get("latitude"), sim.get("longitude")
        if lat is None or lon is None or not points:
            continue
        distance, fire_id = min((_km(lat, lon, fire_lat, fire_lon), fire_id) for fire_id, fire_lat, fire_lon in points)
        if distance <= max_km and fire_id not in matched:
            matched[fire_id] = sim
    return matched


def _hours(detail: dict) -> list[dict]:
    """The hourly polygons, largest first so the smaller ones draw on top."""
    features = (detail.get("result") or {}).get("features") or []
    hours = []
    for feature in features:
        properties = feature.get("properties") or {}
        if feature.get("geometry") is None or properties.get("hour") is None:
            continue
        hour = {"hour": properties["hour"], "geometry": feature["geometry"]}
        if properties.get("burn_probability") is not None:
            hour["burn_probability"] = properties["burn_probability"]
        hours.append(hour)
    return sorted(hours, key=lambda hour: hour["hour"], reverse=True)


def _outcome(detail: dict) -> dict:
    return {"burned_area_m2": (detail.get("summary") or {}).get("burnedAreaM2"), "hours": _hours(detail)}


def _fire(fire_id: str, sim: dict, outcome: dict) -> dict:
    return {
        "fire_id": fire_id,
        "simulation_id": sim["id"],
        "name": sim.get("fireName") or sim.get("locationName") or "",
        "location": sim.get("locationName"),
        "created_at": sim["createdAt"],
        "model": sim.get("model") or "elmfire",
        "duration_hours": sim.get("durationHours"),
        "ensemble_members": sim.get("ensembleMembers") or 1,
        **outcome,
    }


def _refresh() -> list[dict]:
    fires = live.active_fires()["features"]
    since = datetime.now(UTC) - timedelta(hours=LOOKBACK_HOURS)
    matched = match_runs(_fetch_simulations(since), fires)
    if not _runs and (saved := _read_file()) is not None:
        _runs.update({fire["simulation_id"]: _outcome_of(fire) for fire in saved.fires})
    missing = [sim["id"] for sim in matched.values() if sim["id"] not in _runs]
    _runs.update({sim_id: _outcome(detail) for sim_id, detail in _fetch_details(missing).items()})
    wanted = {sim["id"] for sim in matched.values()}
    for sim_id in list(_runs):  # keep only the runs still on the map
        if sim_id not in wanted:
            del _runs[sim_id]
    result = [_fire(fire_id, sim, _runs[sim["id"]]) for fire_id, sim in matched.items()]
    return sorted((fire for fire in result if fire["hours"]), key=lambda fire: fire["created_at"], reverse=True)


def _outcome_of(fire: dict) -> dict:
    return {"burned_area_m2": fire.get("burned_area_m2"), "hours": fire["hours"]}


def predicted_spread() -> dict:
    """The latest completed Deepfire run per active fire, at most CACHE_SECONDS old when Deepfire answers.

    If Deepfire fails, the last good answer (in memory, else from CACHE_FILE) comes back with
    `stale: true`. With neither, raises live.LiveUnavailable.
    """
    global _snapshot
    with _lock:
        now = time.monotonic()
        if _snapshot is None or now >= _snapshot.expires:
            try:
                _snapshot = _Snapshot(_refresh(), datetime.now(UTC), now + CACHE_SECONDS)
            except (httpx.HTTPError, KeyError, TypeError, live.LiveUnavailable) as error:
                fallback = _snapshot or _read_file()
                if fallback is None:
                    raise live.LiveUnavailable(str(error)) from error
                _snapshot = _Snapshot(fallback.fires, fallback.fetched_at, now + RETRY_SECONDS, stale=True)
            else:
                _write_file(_snapshot)
        return _answer(_snapshot)


def _answer(snapshot: _Snapshot) -> dict:
    return {"fires": snapshot.fires, "fetched_at": snapshot.fetched_at.isoformat(), "stale": snapshot.stale}


def _write_file(snapshot: _Snapshot) -> None:
    """The last good answer, for the next outage or restart. A read-only disk only loses the fallback."""
    try:
        temporary = CACHE_FILE.with_suffix(".tmp")
        temporary.write_text(json.dumps(_answer(snapshot)), encoding="utf-8")
        temporary.replace(CACHE_FILE)
    except OSError:
        pass


def _read_file() -> _Snapshot | None:
    try:
        body = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
        return _Snapshot(body["fires"], datetime.fromisoformat(body["fetched_at"]), 0.0)
    except (OSError, ValueError, KeyError):
        return None


def reset_cache() -> None:
    global _snapshot
    _snapshot = None
    _runs.clear()
