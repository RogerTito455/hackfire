"""openrouteservice client: routes that avoid the fire.

Verified against the live API on 2026-09-19. Free plan: 2,000 directions a day, 40 a minute.
"""

import httpx

from ..config import settings
from ..models import TravelMode

_DIRECTIONS = "https://api.openrouteservice.org/v2/directions/{profile}/geojson"
_GET_DIRECTIONS = "https://api.openrouteservice.org/v2/directions/driving-car"
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


def configured() -> bool:
    return bool(settings.ors_api_key)


def ping(client: httpx.Client) -> tuple[int, str]:
    """For the status page (app/provider_status.py): the status code and the start of the body of a
    100 m route. It counts against the daily quota while there is quota left, so the status page asks
    rarely; once the quota is spent ORS answers 403 "Quota exceeded" without counting."""
    response = client.get(
        _GET_DIRECTIONS,
        headers={"Authorization": settings.ors_api_key},
        params={"start": "-4.6,40.4", "end": "-4.601,40.401"},
    )
    return response.status_code, response.text[:300]
