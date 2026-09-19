"""Where the fire is heading: a cone from the front's velocity over the last hours of hotspots.

The replay's predicted spread (PLAN.md section 6). Deepfire's simulation cannot start in the past
(docs/findings/2026-09-19-deepfire-no-historical-simulation.md), so for 23 July we extrapolate:

1. Take the hotspots of the last 2 × WINDOW_H hours and drop isolated ones (fewer than
   MIN_NEIGHBOURS others within NEIGHBOUR_M): stray detections should not steer the front.
2. Direction: from the centroid of the older half to the centroid of the recent half.
3. Speed: how far the leading edge (the LEADING_QUANTILE of positions along that direction)
   moved between the halves, per hour.
4. The predicted area after t hours is the burned area plus the leading edge swept forward
   speed × t, fanning out HALF_ANGLE_DEG either side.

Everything is in local metres (geo.py). It is a heuristic with no wind or terrain: it says where
the recent run points, not what the fire will do.
"""

import math
from dataclasses import dataclass
from datetime import datetime
from functools import cache

import numpy as np
from shapely.geometry import MultiPoint
from shapely.geometry.base import BaseGeometry

from . import geo, replay

WINDOW_H = 3
HORIZON_H = 6
HALF_ANGLE_DEG = 25
LEADING_QUANTILE = 90
NEIGHBOUR_M = 2_000
MIN_NEIGHBOURS = 2
MIN_HOTSPOTS = 10


@dataclass(frozen=True)
class FrontMotion:
    at: datetime
    direction: tuple[float, float]  # unit vector, x east, y north
    speed_m_per_h: float
    leading_edge: tuple[tuple[float, float], ...]  # metres

    @property
    def bearing_deg(self) -> float:
        return (math.degrees(math.atan2(self.direction[0], self.direction[1])) + 360) % 360


@cache
def _arrays() -> tuple[np.ndarray, np.ndarray]:
    times, points = replay._hotspot_times_and_points()
    seconds = np.array([t.timestamp() for t in times])
    metres = np.array([[p.x, p.y] for p in (geo.point_m(lon, lat) for lon, lat in points)]).reshape(-1, 2)
    return seconds, metres


def _clustered(points: np.ndarray) -> np.ndarray:
    """Drop hotspots with fewer than MIN_NEIGHBOURS others within NEIGHBOUR_M."""
    if len(points) == 0:
        return points
    distances = np.linalg.norm(points[:, None, :] - points[None, :, :], axis=2)
    neighbours = (distances <= NEIGHBOUR_M).sum(axis=1) - 1
    return points[neighbours >= MIN_NEIGHBOURS]


@cache
def front_motion(at: datetime) -> FrontMotion | None:
    """The fire front's direction and speed at `at`, or None when it cannot be told apart.

    None when either half of the window has too few hotspots (for example the detection gap on
    23 July between 15:10 and 18:08 UTC) or when the leading edge is not advancing.
    """
    seconds, metres = _arrays()
    now, window = at.timestamp(), WINDOW_H * 3600
    older = _clustered(metres[(seconds > now - 2 * window) & (seconds <= now - window)])
    recent = _clustered(metres[(seconds > now - window) & (seconds <= now)])
    if len(older) < MIN_HOTSPOTS or len(recent) < MIN_HOTSPOTS:
        return None
    drift = recent.mean(axis=0) - older.mean(axis=0)
    if np.linalg.norm(drift) < 1:
        return None
    direction = drift / np.linalg.norm(drift)
    edge_old = np.percentile(older @ direction, LEADING_QUANTILE)
    edge_new = np.percentile(recent @ direction, LEADING_QUANTILE)
    speed = (edge_new - edge_old) / WINDOW_H
    if speed <= 0:
        return None
    leading = recent[recent @ direction >= edge_new]
    return FrontMotion(
        at=at,
        direction=(float(direction[0]), float(direction[1])),
        speed_m_per_h=float(speed),
        leading_edge=tuple((float(x), float(y)) for x, y in leading),
    )


def _rotate(vector: np.ndarray, degrees: float) -> np.ndarray:
    a = math.radians(degrees)
    return np.array([vector[0] * math.cos(a) - vector[1] * math.sin(a), vector[0] * math.sin(a) + vector[1] * math.cos(a)])


def _swept(motion: FrontMotion, hours: float) -> BaseGeometry:
    """The leading edge swept forward `hours`, fanning out ±HALF_ANGLE_DEG."""
    edge = np.array(motion.leading_edge)
    reach = motion.speed_m_per_h * hours
    direction = np.array(motion.direction)
    tips = [edge + _rotate(direction, angle) * reach for angle in (-HALF_ANGLE_DEG, 0, HALF_ANGLE_DEG)]
    return MultiPoint(np.vstack([edge, *tips])).convex_hull.buffer(replay.HOTSPOT_RADIUS_M)


def predicted_area(at: datetime, hours: float) -> BaseGeometry:
    """Burned area at `at` plus where the front is heading within `hours` (metres)."""
    burned = replay.burned_area_m(at)
    motion = front_motion(at)
    return burned if motion is None or hours <= 0 else burned.union(_swept(motion, hours))


def minutes_to_impact(zone: BaseGeometry, at: datetime, step_minutes: int = 10) -> int | None:
    """Minutes until the predicted area first touches `zone` (metres), within HORIZON_H.

    0 when the zone is already inside the burned area; None when the prediction does not reach it.
    """
    if replay.burned_area_m(at).intersects(zone):
        return 0
    motion = front_motion(at)
    if motion is None or not _swept(motion, HORIZON_H).intersects(zone):
        return None
    # The swept area only grows with time, so search for the first step that touches the zone.
    low, high = 1, HORIZON_H * 60 // step_minutes
    while low < high:
        middle = (low + high) // 2
        if _swept(motion, middle * step_minutes / 60).intersects(zone):
            high = middle
        else:
            low = middle + 1
    return low * step_minutes


def hourly_cone(at: datetime) -> list[tuple[int, BaseGeometry]]:
    """(hour, predicted area) for each hour up to HORIZON_H: nested, outermost last."""
    return [(hour, predicted_area(at, hour)) for hour in range(1, HORIZON_H + 1)]

