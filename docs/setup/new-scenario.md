# A new scenario

The demo replays one fire: 23 July 2026 near El Tiemblo, Ávila. Nothing in the code is tied to it. Everything that says *which* fire lives in one file, `data/scenarios/<id>.json`, and `HACKFIRE_SCENARIO` picks the active one (default `el-tiemblo-2026-07-23`). This page is how to add another.

## What a scenario holds

[`data/scenarios/el-tiemblo-2026-07-23.json`](../../data/scenarios/el-tiemblo-2026-07-23.json) is the reference. Read by `backend/app/scenario.py`.

| Field | What it sets | Used by |
|---|---|---|
| `id`, `name` | The scenario's id (its file name) and a plain name | `GET /api/scenario` |
| `bbox` | `[min lon, min lat, max lon, max lat]`. Every downloaded or predicted polygon is clipped to it; the dashboard's map fits it; its middle latitude is where `geo.py` projects to metres | hotspots, zones, spread, routes, the map |
| `time_zone` | IANA name of the local time. Served by `GET /api/scenario`; the dashboard still shows `Europe/Madrid` (see *Still tied* below) | — |
| `replay.start`, `replay.end` | The hotspots `pnpm data:hotspots` downloads, from start up to, not including, end | `data:hotspots` |
| `forecasts.first`, `.last`, `.every_minutes` | When `pnpm data:spread` issues a forecast | `data:spread` |
| `scenario_time` | The moment the calls happen at: routes avoid the fire burned by then, orders are proposed for then, and the agent answers for it until the slider moves. `HACKFIRE_SCENARIO_TIME` overrides it | routes, orders, `get_fire_status` |
| `lead_time.zone`, `.radius_km` | The headline zone, and how near a hotspot must come to count as "reached" | `data:lead-time`, `GET /api/lead-time` |
| `places` | The towns or estates the residents belong to: an OSM node and a radius, from which `pnpm data:zones` takes the residential land use | `data:zones` |
| `files.*` | Paths, relative to the scenario file: `hotspots`, `spread`, `zones`, `lead_time`, `places` (safe points and the crew base), `routes` (the route cache), `registry` (tracked, placeholder phones), `local_registry` (optional, git-ignored, real phones; wins when it exists), `timeline` (the autopilot's script), `calls` (recorded calls the autopilot shows) | everything |

Keys ending in `_note` and `about` are comments: nothing reads them.

## Adding a real scenario

1. **Pick the fire and the box.** Find it with the Deepfire MCP (`deepfire_search_fires`) or [Deepfire](../services/deepfire.md). Keep the box around 40 × 25 km: routes clip the fire to a 14 km square anyway ([finding](../findings/2026-09-19-ors-avoid-polygon-limit.md)).
2. **Write `data/scenarios/<id>.json`** from the reference. Point `files` at new names (for example `../<id>/hotspots.geojson`) so the demo's files stay untouched. Set `HACKFIRE_SCENARIO=<id>` in `.env`.
3. **Hotspots:** `pnpm data:hotspots`. Needs `DEEPFIRE_CLIENT_ID` and `DEEPFIRE_CLIENT_SECRET` and the network; Deepfire returns 503 under load, so retry. Check the log for the feature cap warning.
4. **Zones:** list the residents' towns in `places`, then `pnpm data:zones`. Needs the network, no key ([Overpass](../services/overpass.md)).
5. **Spread:** set `forecasts` to the day that matters, then `pnpm data:spread`. No network. Times with too few recent hotspots get no forecast, which is expected.
6. **Lead time:** set `lead_time.zone` to one of the zone ids, then `pnpm data:lead-time`. No network. It fails when the zone was never flagged before hotspots came within the radius; then there is no lead time to claim for that zone. Check the number against the data before anyone quotes it (CLAUDE.md, *Tone*).
7. **Safe points and the crew base:** write the `places` file by hand from OpenStreetMap (town centres, the nearest fire station). They are demo assumptions, not official meeting points.
8. **Registry:** a tracked file with fictional names and placeholder phones, and if the team wants real calls, a git-ignored local one (`local_registry`) or `HACKFIRE_NEIGHBORS_JSON`. Each resident's `zone` must be a zone id.
9. **Scenario time:** pick a moment after the headline zone is flagged, with time to impact left and safe ways out still open. `GET /api/impact` shows the minutes per zone.
10. **Routes:** `pnpm data:routes`, then `pnpm check:routes`. Needs `ORS_API_KEY` **with quota** (see below).
11. **Autopilot (optional):** a `timeline` like `data/demo_timeline.json`; residents are named by registry position and zones enter it when the forecast first reaches them. `calls` may point at an empty `{"calls": {}}`: the call card then shows no transcript.
12. **Run it:** `pnpm dev:api` and `pnpm dev:web`. The map fits the new box.

## Network, keys and quota

| Step | Network | Key |
|---|---|---|
| `data:hotspots` | Deepfire | `DEEPFIRE_CLIENT_ID`, `DEEPFIRE_CLIENT_SECRET` |
| `data:zones` | Overpass | none |
| `data:spread`, `data:lead-time` | none | none |
| `data:routes` | openrouteservice | `ORS_API_KEY` |
| `check:routes` | none (openrouteservice is cut off) | none |

**openrouteservice quota.** The free plan allows 2,000 directions a day and 40 a minute, and the team's key may be shared and already spent. Each resident costs about 2 × (number of safe points) + 3 requests, so 10 residents and 5 safe points is about 130. `pnpm data:routes` is resumable, and a `403 Quota exceeded` resets at midnight UTC. Without the cache, the demo would ask openrouteservice live, which the demo rule forbids (CLAUDE.md, *Demo mode comes first*).

## Proving nothing changed

- `pnpm data:spread --check` and `pnpm data:lead-time --check` rebuild in memory and compare with the files, writing nothing. The spread depends on the GEOS version under shapely: on 2026-09-19, with shapely 2.1.2 and GEOS 3.13.1, two of the demo's 308 polygons came out one vertex different from the committed file, with the code before scenarios as well as after. Compare against the code before your change, not only against the file.
- `pnpm check:routes` proves every route is cached, with openrouteservice cut off.
- `backend/tests/test_scenario_end_to_end.py` runs the whole chain on a synthetic scenario (`backend/tests/fixtures/straight-fire/`): generated hotspots, the real spread and lead-time pipelines, impact, orders, the agent's tools, triage, the rescue queue, crew alerts, the call-end safety net, the autopilot and Reset, with a router stub. It is part of `pnpm check`.

## Still tied to the demo

- **The dashboard shows times in `Europe/Madrid`** (`REPLAY_TIME_ZONE` in `frontend/src/ui/theme.ts`), whatever the scenario's `time_zone`.
- **Some texts name the demo:** the autopilot note ("not what happened on 23 July", `frontend/src/locales`), the landing page, the pitch and the runbook, and the Galtea scenarios in `backend/app/simulated_residents.py`.
- **The voice agents' prompts** (`voice/`) and `data/demo_calls.json` speak of La Atalaya.
- **The landing page's lead time** is a copy of the demo's (`PUBLISHED_LEAD_TIME` in `frontend/src/domain/leadTime.ts`).
- **One scenario per process.** Switching needs a restart with another `HACKFIRE_SCENARIO`.
