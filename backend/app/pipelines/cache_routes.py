"""Plan every demo route once and cache it, so the live demo does not wait on openrouteservice.

    pnpm data:routes

Needs ORS_API_KEY. For each resident in the registry the backend loads (the local one if present),
plans the evacuation route by car and on foot and the crew's rescue route, all at the scenario
time. Writes data/routes_cache.json: coordinates, directions and geometry, never names or phones.
Rerun it after changing the registry, the scenario time or data/places.json.
"""

import json

from .. import evacuation
from ..models import TravelMode
from ..state import state


def main() -> None:
    for neighbor in state.neighbors():
        for mode in TravelMode:
            route = evacuation.evacuation_route(neighbor, mode, refresh=True)
            print(f"{neighbor.id} {mode:8} {route.distance_m or 0:8.0f} m  {route.spoken_directions[:70]}")
        route = evacuation.rescue_route(neighbor, refresh=True)
        print(f"{neighbor.id} rescue   {route.distance_m or 0:8.0f} m")
    routes = evacuation.export_cache()
    evacuation.CACHE_FILE.write_text(json.dumps(routes, indent=1) + "\n", encoding="utf-8")
    print(f"wrote {len(routes)} routes to {evacuation.CACHE_FILE}")


if __name__ == "__main__":
    main()
