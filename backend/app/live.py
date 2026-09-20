"""Live mode: fires burning right now, from Deepfire, cached so the dashboard never waits on it."""

import time
from dataclasses import dataclass
from datetime import UTC, datetime

import httpx

from .providers import deepfire

# Iberian Peninsula and the Balearic Islands (min lon, min lat, max lon, max lat).
IBERIA_BBOX = "-9.6,35.8,4.4,44.0"
CACHE_SECONDS = 60
TIMEOUT_SECONDS = 10


class LiveUnavailable(Exception):
    """Deepfire failed and there is nothing cached to fall back on."""


@dataclass
class _Snapshot:
    features: list[dict]
    fetched_at: datetime
    monotonic: float


# Norma global keyword used inside a function: this is a process-lifetime cache of Deepfire's last good
# answer, rebound by `active_fires` and cleared by `reset_cache`. Rebinding a module variable is
# what `global` is for; wrapping it in a class would add an object whose only job is to hold it.
_snapshot: _Snapshot | None = None


def _fetch_active_clusters() -> list[dict]:
    with httpx.Client(timeout=TIMEOUT_SECONDS) as client:
        return deepfire.active_clusters(client, deepfire.cached_token(client), IBERIA_BBOX)


def active_fires() -> dict:
    """Active fire clusters as a FeatureCollection, at most CACHE_SECONDS old when Deepfire answers.

    If Deepfire fails (503 under load, timeouts), the last good answer is returned with
    `stale: true`. With nothing cached yet, raises LiveUnavailable.
    """
    global _snapshot
    now = time.monotonic()
    if _snapshot is None or now - _snapshot.monotonic >= CACHE_SECONDS:
        try:
            _snapshot = _Snapshot(_fetch_active_clusters(), datetime.now(UTC), now)
        except (httpx.HTTPError, KeyError) as error:
            if _snapshot is None:
                raise LiveUnavailable(str(error)) from error
            return _collection(_snapshot, stale=True)
    return _collection(_snapshot, stale=False)


def _collection(snapshot: _Snapshot, stale: bool) -> dict:
    return {
        "type": "FeatureCollection",
        "features": snapshot.features,
        "fetched_at": snapshot.fetched_at.isoformat(),
        "stale": stale,
    }


def reset_cache() -> None:
    global _snapshot
    _snapshot = None
