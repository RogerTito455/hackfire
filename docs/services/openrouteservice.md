# openrouteservice

**Used for:** step 3 (resident's route out) and step 4 (crew's route to a rescue). Slice 5 (#6), reused by #9 and #10.
**Status:** provider written, not yet run against the API
**Owner:** Bryan

## Access

Sign up at https://openrouteservice.org/dev/#/signup and create a token. Set `ORS_API_KEY` in `.env`. Issue #1 puts the free plan at 2,000 direction requests a day (not checked against the dashboard yet), which is why routes for the demo residents get cached.

## In the app

`backend/app/providers/routing.py` → `route_avoiding(client, start, end, mode, avoid)`:

- `POST https://api.openrouteservice.org/v2/directions/{profile}/geojson`
- Header `Authorization: <ORS_API_KEY>` (the key itself, no `Bearer`)
- Body `{"coordinates": [[lon, lat], [lon, lat]], "options": {"avoid_polygons": <GeoJSON Polygon or MultiPolygon>}}`
- Profiles: `driving-car` for `mode=car`, `foot-walking` for `mode=walking`

Coordinates are **lon, lat**, as everywhere in GeoJSON.

## In Claude Code

No MCP server. The API reference is enough.

## Gotchas

- **Avoid polygons max out at 200 km² and 20 km in height or width.** The demo box is ~38 × 22 km, so clip the fire to a ≤ 14 km square around the route first. [Finding](../findings/2026-09-19-ors-avoid-polygon-limit.md).
- `spoken_directions` must be read aloud on a call: two or three sentences built from the route's steps, not the full turn-by-turn list.
- 2,000 requests a day is plenty if demo routes are cached, and not if every dashboard poll recomputes them.

## Sources

- Directions API and routing options: https://giscience.github.io/openrouteservice/api-reference/endpoints/directions/routing-options
- Restrictions: https://openrouteservice.org/restrictions/
