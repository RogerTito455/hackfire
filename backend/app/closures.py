"""Roads the coordinator marked as cut. Every route planned after a closure goes around it.

In memory, like the rest of the demo's state, and cleared by a demo reset. A closure is a point on
the road and a radius: routes avoid that circle (evacuation.avoid_polygon), and the route cache is
keyed by the closures in force (fingerprint), so a route from before a closure is never served.
"""

import hashlib
import uuid
from datetime import UTC, datetime

import shapely
from shapely.geometry.base import BaseGeometry

from . import geo
from .models import RoadClosure, RoadClosureRequest

_closures: dict[str, RoadClosure] = {}


def add(request: RoadClosureRequest, affected: list[str] | None = None) -> RoadClosure:
    closure = RoadClosure(
        **request.model_dump(), id=uuid.uuid4().hex[:8], created_at=datetime.now(UTC), affected=affected or []
    )
    _closures[closure.id] = closure
    return closure


def remove(closure_id: str) -> bool:
    return _closures.pop(closure_id, None) is not None


def all() -> list[RoadClosure]:
    return sorted(_closures.values(), key=lambda c: c.created_at)


def area_m() -> BaseGeometry | None:
    """Every closed stretch as one shape, in metres; None when no road is closed."""
    if not _closures:
        return None
    return shapely.union_all([geo.point_m(c.lon, c.lat).buffer(c.radius_m) for c in _closures.values()])


def fingerprint() -> str:
    """Changes whenever the closures in force change; empty when there are none."""
    if not _closures:
        return ""
    parts = sorted(f"{c.lon:.5f},{c.lat:.5f},{c.radius_m:g}" for c in _closures.values())
    return hashlib.sha1("|".join(parts).encode()).hexdigest()[:10]


def forget() -> None:
    _closures.clear()
