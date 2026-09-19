# The route cache did not cover every place a coordinator can order a zone to

**Date:** 2026-09-19 · **Area:** routing, demo mode (#6, #12)

## What happened

`pnpm data:routes` cached each resident's routes to the safe points that **qualify** at the scenario time (three of the five places in `data/places.json`), and the crew's route. But the orders panel lists all five places, marks two of them "not safe now" (El Tiemblo and Cebreros), and `orders.approve()` accepts any of them. A coordinator who sends a zone there makes `GET /api/routes/{id}` and the agent's `get_evacuation_route` call `route_to` for a route that is not in `data/routes_cache.json`. That costs a live openrouteservice request, and without a key, or with the key out of quota, it answers 503 in the middle of the demo.

It went unnoticed because the first version of `pnpm check:routes` (written the same day) enumerated the same three places as the planner and printed `OK`. The reviewer of that change found it. Checking production's five residents with the remote check would also have said `OK`, since a 200 does not say where a route came from.

## What we do about it

- One list, `required_routes` in `backend/app/pipelines/common.py`, is what `pnpm data:routes` plans and `pnpm check:routes` verifies: the nearest safe point, **all five places**, each by car and on foot, and the crew's route. They cannot drift apart again.
- With the check on the committed cache, every resident is missing routes: 4 each for El Tiemblo and Cebreros, and everything for n06 to n10. About 75 openrouteservice requests close it, once there is quota ([the quota](../services/openrouteservice.md#the-quota-and-why-the-demo-must-not-touch-it)).
- Until then, avoid ordering a zone to El Tiemblo or Cebreros in a rehearsal on the deployed service, or leave `ORS_API_KEY` set there only if it has quota.
- If restricting orders to the qualifying places is preferable, that is a product decision for whoever owns the orders panel; then `required_routes` should list `safe_points(at)` again.

## Sources

- `backend/app/orders.py` (`approve`, `safe_point_list`), `frontend/src/ui/OrdersPanel.tsx`
- `backend/app/pipelines/common.py`, `backend/app/pipelines/check_routes.py`
