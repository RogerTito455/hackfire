"""openrouteservice client: routes that avoid the predicted fire."""

import httpx

from ..config import settings
from ..models import TravelMode

_DIRECTIONS = "https://api.openrouteservice.org/v2/directions/{profile}/geojson"
_PROFILE = {TravelMode.CAR: "driving-car", TravelMode.WALKING: "foot-walking"}


def route_avoiding(
    client: httpx.Client,
    start: tuple[float, float],
    end: tuple[float, float],
    mode: TravelMode,
    avoid: dict | None,
) -> dict:
    """Return the ORS GeoJSON route from start to end, both as (lon, lat).

    `avoid` is a GeoJSON Polygon or MultiPolygon. ORS rejects anything over 200 km²
    or 20 km in height or width. The demo box is ~38 × 22 km, so clip the fire polygon
    to a square of at most 14 km around the route before calling.
    """
    body: dict = {"coordinates": [list(start), list(end)]}
    if avoid is not None:
        body["options"] = {"avoid_polygons": avoid}
    response = client.post(
        _DIRECTIONS.format(profile=_PROFILE[mode]),
        headers={"Authorization": settings.ors_api_key},
        json=body,
    )
    response.raise_for_status()
    return response.json()
