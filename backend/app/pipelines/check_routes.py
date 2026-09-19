"""Prove that the API answers every route request without openrouteservice.

    pnpm check:routes                                  # this machine: the registry it loads and data/routes_cache.json
    pnpm check:routes https://<service>.up.railway.app # the deployed service, with the registry it has loaded

The demo must not depend on a third party answering in time, and a route that is not cached costs a
live openrouteservice request that can fail or run out of quota.

Locally it cuts openrouteservice off and asks for every route in `required_routes`, the same list
`pnpm data:routes` plans: each resident's route to the nearest safe point and to every place a
coordinator can order the zone to, by car and on foot, and the crew's route. That is the proof that
the cache is complete.

Against a URL it asks the deployed service, through its public API, for each of its residents' routes
by car, on foot and for the crew, and checks that every answer is a 200 with a drawn route. That proves
the service is up and serves the registry it was given; it cannot see whether an answer came from the
cache (a service with ORS_API_KEY set would fetch a missing route live and still answer 200), which is
why the local check is the one that proves the cache and why the key is best left unset on Railway.

Exit code 0: everything is served. 1: something is missing or the service does not answer.
"""

import sys
from unittest import mock

import httpx

from .. import evacuation
from ..config import settings
from ..providers import routing
from ..state import state
from .common import required_routes


def _offline(*_args, **_kwargs):
    raise httpx.ConnectError("openrouteservice is cut off for this check")


def check_local() -> tuple[dict[str, list[str]], list[str]]:
    """(missing routes by resident, routes that are cached but empty) for the registry this process loaded."""
    at = settings.scenario_time
    missing: dict[str, list[str]] = {}
    empty: list[str] = []
    with mock.patch.object(routing, "route_avoiding", _offline):
        for neighbor in state.neighbors():
            for label, ask in required_routes(neighbor, at):
                try:
                    route = ask()
                except evacuation.RoutingUnavailable:
                    missing.setdefault(neighbor.id, []).append(label)
                else:
                    if route.geometry is None:
                        empty.append(f"{neighbor.id}: {label}")
    print(f"{len(state.neighbors())} residents, {len(evacuation.all_places())} places to order a zone to, scenario time {at.isoformat()}")
    return missing, empty


def check_remote(base: str) -> tuple[dict[str, list[str]], list[str]]:
    """(routes the deployed API does not serve by resident, answers that carry no drawn route)."""
    base = base.rstrip("/")
    missing: dict[str, list[str]] = {}
    empty: list[str] = []
    try:
        with httpx.Client(timeout=60) as client:
            health = client.get(f"{base}/health")
            print(f"{base}/health -> {health.status_code}")
            listing = client.get(f"{base}/api/neighbors")
            if health.status_code != 200 or listing.status_code != 200:
                return {"service": [f"/health {health.status_code}, /api/neighbors {listing.status_code}"]}, []
            residents = listing.json()
            print(f"{len(residents)} residents on the deployed service")
            for resident in residents:
                for label, path in (
                    ("car", f"/api/routes/{resident['id']}?mode=car"),
                    ("walking", f"/api/routes/{resident['id']}?mode=walking"),
                    ("crew", f"/api/rescue-routes/{resident['id']}"),
                ):
                    response = client.get(f"{base}{path}")
                    if response.status_code != 200:
                        missing.setdefault(resident["id"], []).append(f"{label} -> {response.status_code}")
                    elif response.json().get("geometry") is None:
                        empty.append(f"{resident['id']}: {label}")
    except httpx.HTTPError as error:
        return {"service": [f"cannot reach {base}: {error}"]}, []
    return missing, empty


def main() -> None:
    remote = len(sys.argv) > 1
    missing, empty = check_remote(sys.argv[1]) if remote else check_local()
    for route in empty:
        print(f"WARNING: {route} is served without a drawn route (no way that keeps away from the fire)")
    if not missing:
        print("OK: every route is served." if remote else "OK: every route is cached; nothing needs openrouteservice.")
        return
    for resident, routes in sorted(missing.items()):
        print(f"{resident}: {len(routes)} missing, e.g. {routes[0]}")
    print(f"NOT OK: {len(missing)} without every route. `pnpm data:routes` plans what is missing (needs an ORS key with quota).")
    sys.exit(1)


if __name__ == "__main__":
    main()
