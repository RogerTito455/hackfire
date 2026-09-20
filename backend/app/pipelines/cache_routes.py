"""Plan every demo route once and cache it, so the live demo never waits on (or spends) openrouteservice.

    pnpm data:routes             # plan only what is not cached yet; resumable
    pnpm data:routes --refresh   # replan everything and replace the file; all or nothing

Needs ORS_API_KEY. For each resident in the registry the backend loads (the local one if present) it
plans `required_routes` (pipelines/common.py): the route to the nearest safe point and to every place
a coordinator can order the zone to, by car and on foot, and the crew's route, all at the scenario
time. Writes the active scenario's route cache (HACKFIRE_SCENARIO; data/routes_cache.json for the
demo): coordinates, directions and geometry, never names or phones.
Rerun it after changing the registry, the scenario time, data/places.json or the forecasts. The cache
keys hold coordinates and the scenario time, not the forecasts, so a new spread needs `--refresh`.

Without `--refresh`, routes already cached cost nothing, progress is saved after every resident and
on any interruption, and it is safe to interrupt and rerun. Entries of residents that are no longer
in the registry stay: use `--refresh` to drop them. `--refresh` replans everything and writes the
file only when it has finished, so a failure never leaves a mix of old and new routes; the price is
that it cannot resume.

If openrouteservice stops answering (the free plan is 2,000 directions a day and 40 a minute, and the
key may be shared) it says why and exits with code 2. Then:

    pnpm check:routes            # prove that nothing is left to plan
"""

import json
import os
import sys
import time
from unittest import mock

import httpx

from .. import evacuation
from ..providers import routing
from ..scenario import current
from ..state import state
from .common import required_routes

# Norma print() in production code: a command's stdout is its interface, not a log (app/pipelines/__init__.py).

# openrouteservice's free plan allows 40 directions a minute.
PAUSE_SECONDS = 1.6
RATE_LIMIT_WAIT_SECONDS = 65
RATE_LIMIT_RETRIES = 3


def existing_cache() -> dict[str, dict]:
    path = evacuation.cache_file()
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def write_cache(routes: dict[str, dict]) -> None:
    """Replace the file in one step: an interruption must never leave half a cache."""
    path = evacuation.cache_file()
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(dict(sorted(routes.items())), indent=1) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def save(replace: bool) -> int:
    """Write what was planned in this process, merged into the file unless `replace`. Returns its size."""
    planned = evacuation.export_cache()
    routes = planned if replace else {**existing_cache(), **planned}
    write_cache(routes)
    return len(routes)


def explain(error: evacuation.RoutingUnavailable, label: str, refresh: bool) -> str:
    cause = error.__cause__
    status = cause.response.status_code if isinstance(cause, httpx.HTTPStatusError) else None
    if status == 403:
        why = (
            "openrouteservice refused the request: 403, the key's quota is gone. A 'Quota exceeded' resets at\n"
            "midnight UTC (02:00 in Spain). Continue after that, or with another key in ORS_API_KEY."
        )
    elif status == 429:
        why = "openrouteservice is still rate limiting (429) after waiting. Wait a few minutes and rerun."
    else:
        why = f"openrouteservice failed on '{label}': {str(error).splitlines()[0]}"
    kept = (
        f"{evacuation.cache_file().name} is unchanged: --refresh writes only when it finishes."
        if refresh
        else "What was planned is saved; rerun `pnpm data:routes` to plan only what is missing."
    )
    return f"\n{why}\n{kept}"


def main() -> None:
    refresh = "--refresh" in sys.argv
    calls = 0
    real_route = routing.route_avoiding

    def paced_route(*args, **kwargs):
        """Count the real requests, keep under the per-minute limit and wait out a 429.

        Cached routes never get here."""
        nonlocal calls
        for attempt in range(RATE_LIMIT_RETRIES + 1):
            calls += 1
            try:
                return real_route(*args, **kwargs)
            except httpx.HTTPStatusError as error:
                if error.response.status_code != 429 or attempt == RATE_LIMIT_RETRIES:
                    raise
                print(f"  rate limited (429): waiting {RATE_LIMIT_WAIT_SECONDS} s")
                time.sleep(RATE_LIMIT_WAIT_SECONDS)
            finally:
                time.sleep(PAUSE_SECONDS)

    at = current().scenario_time
    label = ""
    try:
        with mock.patch.object(routing, "route_avoiding", paced_route):
            for neighbor in state.neighbors():
                for label, ask in required_routes(neighbor, at, refresh):
                    ask()
                print(f"{neighbor.id}: done ({calls} openrouteservice requests so far)")
                if not refresh:
                    save(replace=False)
    except evacuation.RoutingUnavailable as error:
        total = save(replace=False) if not refresh else len(existing_cache())
        print(explain(error, label, refresh))
        print(f"{total} routes are in {evacuation.cache_file()}")
        sys.exit(2)
    except BaseException:
        if not refresh:
            save(replace=False)  # Ctrl-C or an unexpected error: keep what was planned
        raise
    print(f"wrote {save(replace=refresh)} routes to {evacuation.cache_file()} ({calls} openrouteservice requests)")


if __name__ == "__main__":
    main()
