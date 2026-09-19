"""Planar geometry for the scenario's area.

A scenario's box is some 40 km across, so an equirectangular projection around the box's middle
latitude (40.4°N for El Tiemblo) keeps distances within a fraction of a percent: good enough for
buffers, clipping and "how far is the fire".
"""

import math

import numpy as np
import shapely
from shapely.geometry import Point, box
from shapely.geometry.base import BaseGeometry

from .scenario import cached, current


@cached
def _scale() -> np.ndarray:
    """Metres per degree of longitude and of latitude at the scenario box's middle latitude."""
    return np.array([111_320 * math.cos(math.radians(current().centre_lat)), 110_570])


def to_metres(geometry: BaseGeometry) -> BaseGeometry:
    scale = _scale()
    return shapely.transform(geometry, lambda coords: coords * scale)


def to_degrees(geometry: BaseGeometry) -> BaseGeometry:
    scale = _scale()
    return shapely.transform(geometry, lambda coords: coords / scale)


def point_m(lon: float, lat: float) -> Point:
    x, y = np.array([lon, lat]) * _scale()
    return Point(x, y)


def square_m(center: Point, side: float) -> BaseGeometry:
    half = side / 2
    return box(center.x - half, center.y - half, center.x + half, center.y + half)
