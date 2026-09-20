"""Helpers shared by the pipelines: the cached hotspots and the routes the API must be able to serve."""

import json
from collections.abc import Callable
from datetime import datetime
from pathlib import Path

from .. import evacuation
from ..models import Neighbor, Route, TravelMode
from ..scenario import current
from ..spread import Hotspot

# Norma print() in production code: a command's stdout is its interface, not a log (app/pipelines/__init__.py).


# Recommended by Norma — fixed with Claude Opus 5 via Claude Code
class OutputDiffers(Exception):
    """A `--check` run rebuilt a scenario's cached file and found it different from the one on disk.

    Raised instead of exiting from here: this is a helper two pipelines call, and only an entry point
    decides a process's exit code. `write_or_compare` has already printed which file and why, so the
    `__main__` block that catches this turns it into exit code 1 and says nothing more.
    """


def write_or_compare(path: Path, body: str, what: str, check: bool) -> None:
    """Write a pipeline's output or, with `check`, compare it with the file and raise `OutputDiffers`
    if they differ: the proof that a change to the code left a scenario's cached data as it was,
    without writing."""
    if not check:
        path.write_text(body, encoding="utf-8")
        print(f"wrote {what} to {path}")
        return
    if path.exists() and path.read_text(encoding="utf-8") == body:
        print(f"OK: {path} is unchanged ({what})")
        return
    print(f"DIFFERENT: rebuilding {path} would change it ({what})")
    raise OutputDiffers(str(path))


def read_hotspots() -> list[Hotspot]:
    """The active scenario's cached hotspots as model inputs. Raises if `pnpm data:hotspots` has not
    been run: a pipeline must never write its output from an empty input."""
    collection = json.loads(current().files.hotspots.read_text(encoding="utf-8"))
    return [
        Hotspot(
            lon=f["geometry"]["coordinates"][0],
            lat=f["geometry"]["coordinates"][1],
            observed_at=datetime.fromisoformat(f["properties"]["observed_at"]),
            source=f["properties"]["source"],
            confidence=f["properties"]["confidence"],
        )
        for f in collection["features"]
    ]


def required_routes(
    neighbor: Neighbor, at: datetime, refresh: bool = False
) -> list[tuple[str, Callable[[], Route]]]:
    """Every route the API can be asked for on behalf of a resident, as (label, how to get it).

    The nearest safe point and every place a coordinator can order the zone to, by car and on foot,
    and the crew's route. The orders panel lists every place, the ones marked "not safe now"
    included, so all of them are required, not only the ones that qualify at the scenario time.

    `pnpm data:routes` plans this list and `pnpm check:routes` checks it, so they cannot drift apart.
    The nearest point comes last: it is one of the places, already planned when `refresh` is set.
    """
    routes: list[tuple[str, Callable[[], Route]]] = []
    for place in evacuation.all_places():
        for mode in TravelMode:
            routes.append((f"{place.name}, {mode}", lambda p=place, m=mode: evacuation.route_to(neighbor, p, m, at, refresh)))
    for mode in TravelMode:
        routes.append((f"nearest safe point, {mode}", lambda m=mode: evacuation.evacuation_route(neighbor, m, at)))
    routes.append(("crew route", lambda: evacuation.rescue_route(neighbor, at, refresh)))
    return routes
