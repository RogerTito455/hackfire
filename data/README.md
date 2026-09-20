# Demo data

Static files so the live demo never waits on a third-party API.

Every file below belongs to the demo's scenario, [`scenarios/el-tiemblo-2026-07-23.json`](scenarios/el-tiemblo-2026-07-23.json), which names them and holds the box, the dates, the scenario time and the lead-time zone. `HACKFIRE_SCENARIO` picks another scenario; the pipelines then read and write that one's files. See [A new scenario](../docs/setup/new-scenario.md).

| File | What | Tracked |
|---|---|---|
| `scenarios/<id>.json` | One file per scenario: name, box, replay window, forecast day, scenario time, lead-time zone, the named places for `pnpm data:zones`, and the paths of every file below | Yes |
| `neighbors.sample.json` | The resident registry: 10 households on real OpenStreetMap streets of La Atalaya (4) and El Tiemblo (6), with house numbers where OSM has them, labelled by their street and with placeholder `+34000000001` phones. Written by `pnpm data:registry`, which keeps the residents already in the file (their ids and coordinates are what `demo_timeline.json` and `routes_cache.json` point at) and fills the rest from Overpass | Yes |
| `neighbors.local.json` | 10 residents (6 in La Atalaya, 4 in El Tiemblo) on real OSM streets with invented house numbers and fictional names, and the team's phone numbers in place of `REPLACE-ME-NN`. Wins over the sample when it exists. On Railway the same content is the variable `HACKFIRE_NEIGHBORS_JSON` | **No** (git-ignored) |
| `hotspots_2026-07-22_24.geojson` | 7,068 Deepfire hotspots for the demo box, 22–24 July 2026, sorted by time. Written by `pnpm data:hotspots`, served at `GET /api/hotspots` | Yes |
| `places.json` | Safe points (town centres) and the crew base, from OpenStreetMap. Demo assumptions, not official meeting points | Yes |
| `routes_cache.json` | Every resident's route (car and on foot) to every qualifying safe point, and the crews' routes, planned at the scenario time by `pnpm data:routes`. Coordinates, directions and geometry only; the crews' routes name the resident's address | Yes. 165 routes: the sample registry's 10 residents (`pnpm check:routes` says OK) and the 10 of the local one |
| `spread_2026-07-23.geojson` | Predicted spread for 23 July: a forecast every 30 minutes (UTC) from the front-velocity cone, each with a polygon for now (`hour` 0) and one per hour ahead up to 6. Written by `pnpm data:spread`, served at `GET /api/spread` | Yes |
| `zones.geojson` | 68 places the fire can reach, from OpenStreetMap: La Atalaya and El Tiemblo (ids `la-atalaya`, `el-tiemblo`), care homes, schools, health centres and main roads. Written by `pnpm data:zones`, served at `GET /api/zones` | Yes |
| `demo_timeline.json` | The demo autopilot's script (`backend/app/autopilot.py`, docs/demo/runbook.md): orders approved a set number of minutes after each zone first enters the forecast, and call outcomes a set number of minutes after their zone's order; which recorded transcript each status shows. Residents by position in the registry (1 to 10, which both registries now have). A labelled simulation with the demo residents, not what happened | Yes |
| `demo_calls.json` | Real calls of the resident agent (its prompt, tools and model through SLNG) with residents simulated by Galtea, written by `pnpm eval:galtea -k <scenario> --transcripts data/demo_calls.json` (only passing calls are added). The simulated residents, their names and the address are fictional: no registry data. Reasoning leaked before `</think>` is dropped. Shown by the autopilot's call card. Holds `wheelchair-user` and `refuses-to-leave` (both `needs_rescue`), recorded on 2026-09-19 | Yes |
| `lead_time_la-atalaya.json` | La Atalaya's lead time and how it was computed. Written by `pnpm data:lead-time`, served at `GET /api/lead-time` | Yes |
| `live_spread.json` | Live mode's last good predicted spread: Deepfire's automatic ELMFIRE runs matched to the active fires. Rewritten by the backend every few minutes, served when Deepfire fails (`backend/app/live_spread.py`) | **No** (ignored, runtime cache) |

Demo box (lon/lat): `-4.85,40.30,-4.40,40.50`, the scenario's `bbox`. Keep every polygon clipped to it.
