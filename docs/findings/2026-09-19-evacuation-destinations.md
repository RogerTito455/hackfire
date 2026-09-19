# Sending everyone to one safe point walked some residents into the fire

**Date:** 2026-09-19 · **Area:** routes (#6), predicted spread (#4) · **Found by:** Bryan, from two dashboard screenshots

## What happened

The first route planner sent every resident to the same safe point: the one farthest from the area already burned, which was Cebreros. From La Atalaya that route runs north through El Tiemblo, along the fire's leading edge. It only avoided what had burned, not where the fire was heading, so it was "safe" on paper and pointed people towards the front. Once the predicted spread existed, Cebreros itself turned out to be in the cone, about 3 h away.

## What we do about it

- **Each resident gets their own destination:** the nearest safe point (as the crow flies) that the predicted spread does not reach within 6 h and that is at least 3 km from the burned area (`evacuation.safest_point`). At the scenario time that is Navahondilla, south-west of La Atalaya, away from the fire. `data/places.json` now has five candidates.
- **Residents' routes avoid the burned area plus one hour of predicted spread** (`AVOID_AHEAD_H`), and the agent's sentence says so.
- **When nothing gets out:** the answer is "No route that keeps away from the fire was found. Follow the instructions of the emergency services on site." At 20:30 CEST on 23 July that is what the two sample residents in El Tiemblo get: the fire is predicted to reach the town in about 50 minutes, and the next hour's spread cuts its exits. The agent then classifies them as needing rescue, which is the point of the system. (PLAN.md's sources include an ES-Alert confinement order covering El Tiemblo.)
- **Crews are different:** their routes avoid only what has burned, and if even that blocks every road they get the direct route with a spoken warning first. Crews work inside the fire's path; residents never get a route through it.

## Sources

- `errors/Route1.png`, `errors/Route2.png` (local screenshots, not committed)
- `backend/app/evacuation.py`, `backend/app/spread.py`; tests in `backend/tests/test_routes.py`
