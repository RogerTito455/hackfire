"""openrouteservice client: routes that avoid the fire.

Verified against the live API on 2026-09-19. Free plan: 2,000 directions a day, 40 a minute.
"""

import httpx

from ..config import settings
from ..models import TravelMode

_DIRECTIONS = "https://api.openrouteservice.org/v2/directions/{profile}/geojson"
_PROFILE = {TravelMode.CAR: "driving-car", TravelMode.WALKING: "foot-walking"}

# ORS error code for "no route between these points" (for example, every road is avoided).
ROUTE_NOT_FOUND = 2009


class NoRouteFound(Exception):
    """ORS answered, but there is no route that respects the avoided area."""


def route_avoiding(
    client: httpx.Client,
    start: tuple[float, float],
    end: tuple[float, float],
    mode: TravelMode,
    avoid: dict | None,
) -> dict:
    """Return the ORS GeoJSON route feature from start to end, both as (lon, lat).

    `avoid` is a GeoJSON Polygon or MultiPolygon. ORS rejects anything over 200 km²
    or 20 km in height or width. The demo box is ~38 × 22 km, so clip the fire polygon
    to a square of at most 14 km around the route before calling.
    """
    body: dict = {
        "coordinates": [list(start), list(end)],
        "instructions": True,
        "language": "en",
        "units": "m",
        # Homes and town centres can sit a few hundred metres from the nearest routable road.
        "radiuses": [-1, -1],
    }
    if avoid is not None:
        body["options"] = {"avoid_polygons": avoid}
    response = client.post(
        _DIRECTIONS.format(profile=_PROFILE[mode]),
        headers={"Authorization": settings.ors_api_key},
        json=body,
    )
    if response.status_code == 404 and response.json().get("error", {}).get("code") == ROUTE_NOT_FOUND:
        raise NoRouteFound(response.json()["error"].get("message", "no route"))
    response.raise_for_status()
    return response.json()["features"][0]
