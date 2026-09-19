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

## Evacuation orders per zone (done)

In practice the authority orders a **whole zone** at once ("everyone in La Atalaya: leave for X"), so the message is the same for every neighbour and arrivals can be counted. HackFire now works that way (`backend/app/orders.py`):

1. **The system proposes** one order per zone with residents: leave for the nearest safe point the forecast does not reach, measured from the zone's centre, or stay indoors when there is none.
2. **The coordinator approves or changes it** in the dashboard's *Evacuation orders* panel: any safe point, marked "not safe now" when it does not qualify, or stay indoors.
3. **Once approved, the agent reads it to everyone in the zone.** `get_fire_status` ends with the order ("The order for La Atalaya is to leave now for San Martín de Valdeiglesias."). `get_evacuation_route` starts with it and leads each resident, by their own route, to that destination; a stay-indoors order replaces the route.
4. Unapproved zones keep the per-resident nearest safe point. Reset clears every order.

`pnpm data:routes` caches every resident's route to every qualifying safe point, so a changed order is still served without openrouteservice.

## Sources

- `errors/Route1.png`, `errors/Route2.png` (local screenshots, not committed)
- `backend/app/evacuation.py`, `backend/app/impact.py`; tests in `backend/tests/test_routes.py`
- `data/lead_time_la-atalaya.json` (flagged 13:30 UTC)
