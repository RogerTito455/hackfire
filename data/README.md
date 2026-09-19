# Demo data

Static files so the live demo never waits on a third-party API.

| File | What | Tracked |
|---|---|---|
| `neighbors.sample.json` | Placeholder resident registry | Yes |
| `neighbors.local.json` | Real addresses and the team's phone numbers | **No** (git-ignored) |
| `hotspots_2026-07-22_24.geojson` | 7,068 Deepfire hotspots for the demo box, 22–24 July 2026, sorted by time. Written by `pnpm data:hotspots`, served at `GET /api/hotspots` | Yes |
| `places.json` | Safe points (town centres) and the crew base, from OpenStreetMap. Demo assumptions, not official meeting points | Yes |
| `routes_cache.json` | Every demo route planned at the scenario time, written by `pnpm data:routes`. Coordinates, directions and geometry only | Yes, for the sample registry |
| `spread_2026-07-23.geojson` | Predicted spread for 23 July: a forecast every 30 minutes (UTC) from the front-velocity cone, each with a polygon for now (`hour` 0) and one per hour ahead up to 6. Written by `pnpm data:spread`, served at `GET /api/spread` | Yes |
| `zones.geojson` | 68 places the fire can reach, from OpenStreetMap: La Atalaya and El Tiemblo (ids `la-atalaya`, `el-tiemblo`), care homes, schools, health centres and main roads. Written by `pnpm data:zones`, served at `GET /api/zones` | Yes |
| `lead_time_la-atalaya.json` | La Atalaya's lead time and how it was computed. Written by `pnpm data:lead-time`, served at `GET /api/lead-time` | Yes |

Demo box (lon/lat): `-4.85,40.30,-4.40,40.50`. Keep every polygon clipped to it.
