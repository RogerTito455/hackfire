"""Live mode's official road data: the DGT's forest-fire incidents and road closures across Spain.

Official data, published by the DGT (Spain's traffic authority) on its National Access Point as
DATEX II (providers/dgt.py). HackFire only reads it and shows it next to its own suggestions: the
forest-fire incidents on the map, and, for the selected fire, the DGT records within its simulated
footprint plus NEAR_FIRE_M.

The feed is about 3 MB, so the relevant records are cached in memory for CACHE_SECONDS and the last
good answer is written to CACHE_FILE. When the DGT does not answer, the last one comes back with
`stale: true`; with none, DgtUnavailable.
"""

import json
import threading
import time
from dataclasses import dataclass
from datetime import UTC, datetime

import httpx
from shapely.geometry import LineString, Point

from .config import DATA_DIR
from .providers import dgt

CACHE_FILE = DATA_DIR / "live_dgt.json"
CACHE_SECONDS = 300
# After a failure, the stale answer is served this long before the DGT is asked again.
RETRY_SECONDS = 60
TIMEOUT_SECONDS = 10
# DGT records this far from a fire's simulated footprint are listed with it.
NEAR_FIRE_M = 5000

SOURCE = "DGT"
SOURCE_NAME = "DGT, Punto de Acceso Nacional (DATEX II)"


class DgtUnavailable(Exception):
    """The DGT feed failed and nothing is cached."""


@dataclass
class _Snapshot:
    records: list[dict]
    published_at: str | None
    fetched_at: datetime
    expires: float  # time.monotonic()
    stale: bool = False


_snapshot: _Snapshot | None = None
_lock = threading.Lock()


def relevant(records: list[dict]) -> list[dict]:
    """Forest-fire incidents and road or carriageway closures, the only records live mode shows. Pure."""
    return [
        record
        for record in records
        if (record["forest_fire"] or record["closure"]) and record.get("validity") in (None, "active")
    ]


def _fetch() -> tuple[list[dict], str | None]:
    with httpx.Client(timeout=TIMEOUT_SECONDS) as client:
        feed = dgt.parse(dgt.fetch(client))
    return relevant(feed["records"]), feed["published_at"]


def _answer(snapshot: _Snapshot) -> dict:
    return {
        "source": SOURCE,
        "source_name": SOURCE_NAME,
        "published_at": snapshot.published_at,
        "fetched_at": snapshot.fetched_at.isoformat(),
        "stale": snapshot.stale,
        "records": snapshot.records,
    }


def _write_file(snapshot: _Snapshot) -> None:
    """The last good answer, for the next outage or restart. A read-only disk only loses the fallback."""
    try:
        CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        temporary = CACHE_FILE.with_suffix(".tmp")
        temporary.write_text(json.dumps(_answer(snapshot), separators=(",", ":")), encoding="utf-8")
        temporary.replace(CACHE_FILE)
    except OSError:
        pass


def _read_file() -> _Snapshot | None:
    try:
        body = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
        return _Snapshot(body["records"], body.get("published_at"), datetime.fromisoformat(body["fetched_at"]), 0.0)
    except (OSError, ValueError, KeyError, TypeError):
        return None


def snapshot() -> dict:
    """The DGT's forest-fire incidents and closures, at most CACHE_SECONDS old when the DGT answers.

    If the DGT fails, the last good answer (in memory, else from CACHE_FILE) comes back with
    `stale: true`. With neither, raises DgtUnavailable.
    """
    global _snapshot
    with _lock:
        now = time.monotonic()
        if _snapshot is None or now >= _snapshot.expires:
            try:
                records, published_at = _fetch()
                _snapshot = _Snapshot(records, published_at, datetime.now(UTC), now + CACHE_SECONDS)
            except (httpx.HTTPError, ValueError) as error:
                fallback = _snapshot or _read_file()
                if fallback is None:
                    raise DgtUnavailable(str(error)) from error
                _snapshot = _Snapshot(fallback.records, fallback.published_at, fallback.fetched_at, now + RETRY_SECONDS, stale=True)
            else:
                _write_file(_snapshot)
        return _answer(_snapshot)


def overview() -> dict:
    """GET /api/live/dgt: the whole of Spain, forest-fire incidents and closures apart."""
    body = snapshot()
    records = body.pop("records")
    return {
        **body,
        "forest_fires": [record for record in records if record["forest_fire"]],
        "closures": [record for record in records if record["closure"] and not record["forest_fire"]],
    }


def _shape(record: dict):
    start, end = record["from"], record.get("to")
    if end is None or (start["lon"], start["lat"]) == (end["lon"], end["lat"]):
        return Point(start["lon"], start["lat"])
    return LineString([(start["lon"], start["lat"]), (end["lon"], end["lat"])])


def near(records: list[dict], area) -> list[dict]:
    """The records whose point or stretch touches `area` (lon/lat), forest fires first, newest first. Pure."""
    found = [record for record in records if _shape(record).intersects(area)]
    found.sort(key=lambda record: record.get("since") or "", reverse=True)
    return sorted(found, key=lambda record: not record["forest_fire"])


def near_area(area) -> dict:
    """For one fire: the DGT records within `area`, or why there are none. Never raises."""
    try:
        body = snapshot()
    except DgtUnavailable:
        return {"source": SOURCE, "source_name": SOURCE_NAME, "available": False, "stale": False, "records": []}
    return {**body, "available": True, "near_m": NEAR_FIRE_M, "records": near(body["records"], area)}


def reset_cache() -> None:
    global _snapshot
    _snapshot = None
