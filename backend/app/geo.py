"""Planar geometry for the demo area.

The demo box is ~40 km across, so an equirectangular projection around 40.4°N keeps distances
within a fraction of a percent: good enough for buffers, clipping and "how far is the fire".
"""

import math

import numpy as np
import shapely
from shapely.geometry import Point, box
from shapely.geometry.base import BaseGeometry

LAT0 = 40.4
_SCALE = np.array([111_320 * math.cos(math.radians(LAT0)), 110_570])


def to_metres(geometry: BaseGeometry) -> BaseGeometry:
    return shapely.transform(geometry, lambda coords: coords * _SCALE)


def to_degrees(geometry: BaseGeometry) -> BaseGeometry:
    return shapely.transform(geometry, lambda coords: coords / _SCALE)


def point_m(lon: float, lat: float) -> Point:
    x, y = np.array([lon, lat]) * _SCALE
    return Point(x, y)


def square_m(center: Point, side: float) -> BaseGeometry:
    half = side / 2
    return box(center.x - half, center.y - half, center.x + half, center.y + half)
