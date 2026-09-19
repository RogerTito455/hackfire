# openrouteservice

**Used for:** step 3 (resident's route out) and step 4 (crew's route to a rescue). Slice 5 (#6), reused by #9 and #10.
**Status:** working. Both routing tools are real; 15 demo routes cached in `data/routes_cache.json`
**Owner:** Bryan

## Access

Sign up at https://openrouteservice.org/dev/#/signup and create a token. Set `ORS_API_KEY` in `.env`. The free plan's dashboard shows **2,000 directions a day and 40 a minute** (checked 2026-09-19). The demo needs about 30 (each resident by car and on foot, plus rescue routes), and they are cached, so the quota is not a concern.

## In the app

`backend/app/providers/routing.py` → `route_avoiding(client, start, end, mode, avoid)`:

- `POST https://api.openrouteservice.org/v2/directions/{profile}/geojson`
- Header `Authorization: <ORS_API_KEY>` (the key itself, no `Bearer`)
- Body `{"coordinates": [[lon, lat], [lon, lat]], "options": {"avoid_polygons": <GeoJSON Polygon or MultiPolygon>}}`
- Profiles: `driving-car` for `mode=car`, `foot-walking` for `mode=walking`

Coordinates are **lon, lat**, as everywhere in GeoJSON. The provider also asks for English instructions and `radiuses: [-1, -1]`, so homes and town centres a few hundred metres from a road still snap to it. ORS error 2009 ("no route") becomes `NoRouteFound`.

### How a route is planned (`backend/app/evacuation.py`)

1. **What to avoid:** for residents, every hotspot observed up to the scenario time (`HACKFIRE_SCENARIO_TIME`, default 23 July 16:00 UTC, 18:00 CEST), buffered by 750 m and merged (`replay.burned_area_m`), **plus one hour of predicted spread** from the forecast in force (`impact.predicted_footprint`). Clipped to a 14 km square around the route's midpoint, with 500 m clearings around the start and end. For crews, only what has burned; if that blocks every road, they get the direct route with a spoken warning.
2. **Where to go:** the destination of the zone's approved evacuation order (`orders.py`); without one, each resident goes to the nearest safe point in `data/places.json` that the forecast does not reach within 6 h and that is at least 3 km from the fire: at the default time, San Martín de Valdeiglesias for La Atalaya and Navahondilla for El Tiemblo. With no safe way out the answer says so. See [the finding](../findings/2026-09-19-evacuation-destinations.md). The crew's rescue routes start at the El Tiemblo fire station (OSM node 5582810191).
3. **What the agent says:** the three longest named roads in driving order, the distance, and the time ("around 2 hours and 20 minutes on foot"). Many main roads are unnamed in OSM, and then the sentence names only the destination. The route from La Atalaya to Cebreros runs on asphalt (checked with `extra_info: waytype, surface`).
4. **Cache:** memory, then `data/routes_cache.json`, then ORS. `pnpm data:routes` replans every resident at the scenario time. Rerun it after changing the registry, the scenario time or `places.json`.

| Endpoint | For |
|---|---|
| `POST /tools/get_evacuation_route` | The agent: `{address, mode}`, the address as the registry has it |
| `POST /tools/get_rescue_route` | The agent or crew: `{rescue_id}` |
| `GET /api/routes/{neighbor_id}?mode=car` | The dashboard: click a resident to draw their route |
| `GET /api/fire-area` | The dashboard: the burned area the routes avoid |

## In Claude Code

No MCP server. The API reference is enough.

## Gotchas

- **Avoid polygons max out at 200 km² and 20 km in height or width.** The demo box is ~38 × 22 km, so clip the fire to a ≤ 14 km square around the route first. [Finding](../findings/2026-09-19-ors-avoid-polygon-limit.md).
- `spoken_directions` must be read aloud on a call: two or three sentences built from the route's steps, not the full turn-by-turn list.
- Routes are planned at a fixed scenario time, not at the dashboard's slider time: the fire area drawn with a route says which time it is.
- The avoided area is what has burned so far, not the predicted spread. When #4 lands, add the predicted polygon for the next hours to `avoid_polygon`.

## Sources

- Directions API and routing options: https://giscience.github.io/openrouteservice/api-reference/endpoints/directions/routing-options
- Restrictions: https://openrouteservice.org/restrictions/
