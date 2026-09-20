"""A navigation link for a route we planned, so the crew's phone follows our way, not its own.

Google Maps recomputes the road between the points it is given, so a link with only the two ends
can send a crew straight through the fire. The middle of our route goes in as waypoints, which the
app has to visit in order. It can still reroute around what it knows and we do not (a crash, a jam),
so the route the coordinator sees stays the one that counts.
"""

DIRECTIONS = "https://www.google.com/maps/dir/?api=1"
# Maps takes up to nine waypoints; three keep the link short and the shape ours.
WAYPOINTS = 3


def navigate(coordinates: list[list[float]], waypoints: int = WAYPOINTS) -> str:
    """A Google Maps driving link along a GeoJSON LineString's coordinates (lon, lat)."""
    if len(coordinates) < 2:
        raise ValueError("a route needs at least two points")
    middle = [coordinates[len(coordinates) * (i + 1) // (waypoints + 1)] for i in range(waypoints)]
    middle = [point for point in middle if point not in (coordinates[0], coordinates[-1])]
    parts = [DIRECTIONS, f"origin={_point(coordinates[0])}", f"destination={_point(coordinates[-1])}"]
    if middle:
        parts.append("waypoints=" + "%7C".join(_point(point) for point in middle))
    parts.append("travelmode=driving")
    return parts[0] + "&" + "&".join(parts[1:])


def _point(coordinate: list[float]) -> str:
    """Maps writes a point as lat,lon; GeoJSON writes it the other way round."""
    return f"{coordinate[1]:.5f},{coordinate[0]:.5f}"
