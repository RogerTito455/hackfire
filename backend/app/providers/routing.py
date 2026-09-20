"""openrouteservice client: routes that avoid the fire.

Verified against the live API on 2026-09-19. Free plan: 2,000 directions a day and 40 a minute, per
key. `settings.ors_api_keys` holds the keys in the order they are tried (ORS_API_KEY, ORS_API_KEY2,
ORS_API_KEY3): when one answers "quota exceeded" the next one takes over, so a long
`pnpm data:routes` does not stop at the first spent key.
"""

import logging

import httpx

from ..config import settings
from ..models import TravelMode

logger = logging.getLogger(__name__)

_DIRECTIONS = "https://api.openrouteservice.org/v2/directions/{profile}/geojson"
_GET_DIRECTIONS = "https://api.openrouteservice.org/v2/directions/driving-car"
# Two points 40 m apart on the same road out of El Tiemblo, taken from a route ORS itself planned.
# The check used to ask for a route between two points in the middle of a field, and ORS answered
# 404 "Could not find routable point": the status panel then said openrouteservice was down while
# routing worked. A point ORS has already snapped to cannot give that answer.
_PING_FROM = "-4.453165,40.381927"
_PING_TO = "-4.453632,40.382094"
_PROFILE = {TravelMode.CAR: "driving-car", TravelMode.WALKING: "foot-walking"}

# ORS error code for "no route between these points" (for example, every road is avoided).
ROUTE_NOT_FOUND = 2009

# The keys whose daily quota ran out while this process was running, by position in
# `settings.ors_api_keys`. The allowance resets at midnight UTC, so this is remembered for the
# process only, and a restart tries every key again. A 429 (40 a minute) moves to the next key
# without marking this one spent: it is a pause, not an allowance that is gone.
_spent: set[int] = set()


class NoRouteFound(Exception):
    """ORS answered, but there is no route that respects the avoided area."""


def keys() -> list[tuple[int, str]]:
    """The keys still worth trying, as (position, key), in order.

    Never empty: with every key spent (or none configured) it keeps the last one, so the caller gets
    the real refusal from openrouteservice — the same 403 as before there were several keys, which
    `evacuation.plan` turns into `RoutingUnavailable`. Asking with a spent key costs no quota.
    """
    live = [(index, key) for index, key in enumerate(settings.ors_api_keys) if index not in _spent]
    return live or list(enumerate(settings.ors_api_keys))[-1:] or [(0, "")]


def quota_is_gone(response: httpx.Response) -> bool:
    """Whether this refusal means the key's daily allowance is spent: ORS answers 403 with a quota
    message. `Access to this API has been disallowed` is also a 403 and is not one."""
    return response.status_code == 403 and "quota" in response.text.lower()


def _try_next_key(response: httpx.Response, index: int, remaining: int) -> bool:
    """Whether to move on to the next key, remembering a spent one. Never logs a key."""
    if quota_is_gone(response):
        _spent.add(index)
        moving = f"moving to key {index + 2}" if remaining else "no key left to try"
        logger.warning("openrouteservice key %d's daily quota is spent: %s", index + 1, moving)
        return bool(remaining)
    if response.status_code == 429 and remaining:
        logger.warning("openrouteservice key %d is rate limited (429): moving to key %d", index + 1, index + 2)
        return True
    return False


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
    candidates = keys()
    for attempt, (index, key) in enumerate(candidates):
        response = client.post(
            _DIRECTIONS.format(profile=_PROFILE[mode]),
            headers={"Authorization": key},
            json=body,
        )
        if _try_next_key(response, index, remaining=len(candidates) - attempt - 1):
            continue
        if response.status_code == 404 and response.json().get("error", {}).get("code") == ROUTE_NOT_FOUND:
            raise NoRouteFound(response.json()["error"].get("message", "no route"))
        response.raise_for_status()
        return response.json()["features"][0]
    raise AssertionError("unreachable: the last key is never skipped")


def configured() -> bool:
    return bool(settings.ors_api_keys)


def ping(client: httpx.Client) -> tuple[int, str]:
    """For the status page (app/provider_status.py): the status code and the start of the body of a
    100 m route, asked with the first key that has quota left. It counts against the daily quota while
    there is quota left, so the status page asks rarely; once the quota is spent ORS answers 403
    "Quota exceeded" without counting."""
    response = client.get(
        _GET_DIRECTIONS,
        headers={"Authorization": keys()[0][1]},
        params={"start": _PING_FROM, "end": _PING_TO},
    )
    return response.status_code, response.text[:300]
