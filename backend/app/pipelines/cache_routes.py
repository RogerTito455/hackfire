"""Plan every demo route once and cache it, so the live demo does not wait on openrouteservice.

    pnpm data:routes

Needs ORS_API_KEY. For each resident in the registry the backend loads (the local one if present),
plans the route by car and on foot to every safe point that qualifies (the coordinator may order a
zone to any of them) and the crew's rescue route, all at the scenario time. Writes data/routes_cache.json: coordinates, directions and geometry, never names or phones.
Rerun it after changing the registry, the scenario time or data/places.json.
"""

import json
import time

from .. import evacuation
from ..config import settings
from ..models import TravelMode
from ..state import state

# openrouteservice's free plan allows 40 directions a minute.
PAUSE_SECONDS = 1.6


def main() -> None:
    at = settings.scenario_time
    targets = evacuation.safe_points(at)
    for neighbor in state.neighbors():
        # Every safe point, not only the nearest: the coordinator may order a zone elsewhere.
        for target in targets:
            for mode in TravelMode:
                route = evacuation.route_to(neighbor, target, mode, refresh=True)
                print(f"{neighbor.id} {mode:8} → {target.name[:24]:24} {route.distance_m or 0:8.0f} m")
                time.sleep(PAUSE_SECONDS)
        for mode in TravelMode:
            evacuation.evacuation_route(neighbor, mode)  # the nearest one, already planned above
        route = evacuation.rescue_route(neighbor, refresh=True)
        print(f"{neighbor.id} rescue   {route.distance_m or 0:8.0f} m")
        time.sleep(PAUSE_SECONDS)
    routes = evacuation.export_cache()
    evacuation.CACHE_FILE.write_text(json.dumps(routes, indent=1) + "\n", encoding="utf-8")
    print(f"wrote {len(routes)} routes to {evacuation.CACHE_FILE}")


if __name__ == "__main__":
    main()
