# Demo data

Static files so the live demo never waits on a third-party API.

| File | What | Tracked |
|---|---|---|
| `neighbors.sample.json` | Placeholder resident registry | Yes |
| `neighbors.local.json` | 10 residents (6 in La Atalaya, 4 in El Tiemblo) on real OSM streets with invented house numbers and fictional names, and the team's phone numbers in place of `REPLACE-ME-NN`. Wins over the sample when it exists. On Railway the same content is the variable `HACKFIRE_NEIGHBORS_JSON` | **No** (git-ignored) |
| `hotspots_2026-07-22_24.geojson` | 7,068 Deepfire hotspots for the demo box, 22–24 July 2026, sorted by time. Written by `pnpm data:hotspots`, served at `GET /api/hotspots` | Yes |
| `places.json` | Safe points (town centres) and the crew base, from OpenStreetMap. Demo assumptions, not official meeting points | Yes |
| `routes_cache.json` | Every resident's route (car and on foot) to every qualifying safe point, and the crews' routes, planned at the scenario time by `pnpm data:routes`. Coordinates, directions and geometry only; the crews' routes name the resident's address | Yes. Covers residents n01 to n05 (the sample registry, and the first five of the 10-resident one). **n06 to n10 are not cached yet**: run `pnpm data:routes` with an ORS key that still has quota (about 70 requests) |
| `spread_2026-07-23.geojson` | Predicted spread for 23 July: a forecast every 30 minutes (UTC) from the front-velocity cone, each with a polygon for now (`hour` 0) and one per hour ahead up to 6. Written by `pnpm data:spread`, served at `GET /api/spread` | Yes |
| `zones.geojson` | 68 places the fire can reach, from OpenStreetMap: La Atalaya and El Tiemblo (ids `la-atalaya`, `el-tiemblo`), care homes, schools, health centres and main roads. Written by `pnpm data:zones`, served at `GET /api/zones` | Yes |
| `demo_timeline.json` | The demo autopilot's script (`backend/app/autopilot.py`, docs/demo/runbook.md): orders approved and call outcomes at replay moments on 23 July, after La Atalaya is first flagged. Residents by position in the registry (1 to 10; the sample skips 6 to 10). A labelled simulation with the demo residents, not what happened | Yes |
| `lead_time_la-atalaya.json` | La Atalaya's lead time and how it was computed. Written by `pnpm data:lead-time`, served at `GET /api/lead-time` | Yes |
| `live_spread.json` | Live mode's last good predicted spread: Deepfire's automatic ELMFIRE runs matched to the active fires. Rewritten by the backend every few minutes, served when Deepfire fails (`backend/app/live_spread.py`) | **No** (ignored, runtime cache) |

Demo box (lon/lat): `-4.85,40.30,-4.40,40.50`. Keep every polygon clipped to it.
