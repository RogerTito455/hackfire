# Demo data

Static files so the live demo never waits on a third-party API.

| File | What | Tracked |
|---|---|---|
| `neighbors.sample.json` | Placeholder resident registry | Yes |
| `neighbors.local.json` | Real addresses and the team's phone numbers | **No** (git-ignored) |
| `hotspots_2026-07-22_24.geojson` | Deepfire hotspots for the demo box, written by `pnpm data:hotspots` | Yes |
| `spread_2026-07-23.geojson` | Cached Deepfire spread simulation, one polygon per hour | Yes |
| `zones.geojson` | Towns, estates, care homes and roads from OSM | Yes |

Demo box (lon/lat): `-4.85,40.30,-4.40,40.50`. Keep every polygon clipped to it.
