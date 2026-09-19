# Sending everyone to one safe point walked some residents into the fire

**Date:** 2026-09-19 · **Area:** routes (#6), predicted spread (#4) · **Found by:** Bryan, from two dashboard screenshots

## What happened

The first route planner sent every resident to the same safe point: the one farthest from the area already burned, which was Cebreros. From La Atalaya that route runs north through El Tiemblo, along the fire's leading edge. It avoided only what had burned, not where the fire was heading, so it was "safe" on paper and pointed people towards the front.

## What we do about it

- **Each resident gets their own destination:** the nearest safe point (as the crow flies) that the forecast in force does not reach within its 6 hours, and that is at least 3 km from the burned area (`evacuation.safest_point`, reading `impact.predicted_footprint`). `data/places.json` now has five candidates.
- **Residents' routes avoid the burned area plus one hour of predicted spread** (`AVOID_AHEAD_H`), and the agent's sentence says so.
- **No safe way out** gets a plain answer: "No route that keeps away from the fire was found. Follow the instructions of the emergency services on site." The agent then classifies the resident as needing rescue.
- **Crews are different:** their routes avoid only what has burned, and if even that blocks every road they get the direct route with a spoken warning first. Crews work inside the fire's path; residents never get a route through it.
- **The scenario time moved to 16:00 UTC (18:00 CEST).** With the forecast from #31, La Atalaya is first flagged at 15:30 CEST. By 20:30 CEST, the old default, the forecast already covers the estate and no one has a safe way out. At 18:00 CEST it is about 4 h from impact: La Atalaya goes to San Martín de Valdeiglesias (6 km) and El Tiemblo to Navahondilla.

## Next

In practice the authority assigns destinations **per zone** ("everyone in La Atalaya: go to X by road Y"), so the message is the same for a whole area and people can be counted on arrival. The proposal: the system suggests a destination per zone at risk, the coordinator confirms or changes it when approving the call campaign (#8), and the agent reads that order to everyone in the zone, with each resident's own route to it.

## Sources

- `errors/Route1.png`, `errors/Route2.png` (local screenshots, not committed)
- `backend/app/evacuation.py`, `backend/app/impact.py`; tests in `backend/tests/test_routes.py`
- `data/lead_time_la-atalaya.json` (flagged 13:30 UTC)
