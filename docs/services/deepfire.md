# Deepfire

**Used for:** step 1 (hotspots, live fires) and step 2 (predicted spread). Slices 2, 3 and 10 (#3, #4, #11).
**Status:** hotspots working (7,068 cached for the replay, `GET /api/hotspots`); live mode working (`GET /api/live/fires`); spread not started
**Owners:** Bryan (hotspots, live mode), Rosa (spread)

## Access

https://app.deepfire.co → Settings → API clients → Create. Set `DEEPFIRE_CLIENT_ID` and `DEEPFIRE_CLIENT_SECRET` in `.env`; those are the exact names the code and the Deepfire docs use.

## In the app

`backend/app/providers/deepfire.py`. Base URL `https://api.deepfire.co`.

| What | Request | Notes |
|---|---|---|
| Token | `POST /v1/token` with `{"client_id", "client_secret"}` | Returns `access_token`, valid ~180 days, no refresh token. Send as `Authorization: Bearer` |
| Hotspots | `GET /ogc/features/v1/collections/deepfire:hotspots/items` | `bbox`, `datetime` (closed interval only) or a `cql2-text` `filter`, `f=application/geo+json`. History goes back to January 2025 |
| Active fires | `GET /ogc/features/v1/collections/deepfire:clusters/items` | `filter=active = true` |
| Spread | `POST /v1/fire-spread/simulations` | See below |

Download the replay data once and commit it:

```bash
pnpm data:hotspots     # writes data/hotspots_2026-07-22_24.geojson
```

First run on 2026-09-19: about a minute, 7,068 hotspots, one cluster, no 3-hour window near the cap. The pipeline keeps only what the replay needs (`observed_at`, `fire_radiative_power`, `confidence`, `source`, `cluster_id`), rounds coordinates to 5 decimals and sorts by time: 2.2 MB on disk, ~250 KB gzipped over the wire. Sources: MTG (geostationary, every 10 minutes) 62%, VIIRS 29%, MODIS 5%, Sentinel-3 5%.

### Live mode

`backend/app/live.py` asks for active clusters (`filter=active = true`) over `-9.6,35.8,4.4,44.0`, which covers Iberia plus bits of southern France and northern Algeria. Clusters are bare points: `id`, `first_observed`, `last_observed`, `active`, with no country and no name. On 2026-09-19 at 16:17 CEST there were 116, returned in 0.6 s.

The backend caches the answer for 60 s and reuses one token for the life of the process. If Deepfire fails, it serves the last good answer marked `stale: true`; with nothing cached, it returns a 503, which the dashboard shows as a message. The dashboard polls every 60 s, only while live mode is on.

### Predicted spread in the replay (`backend/app/spread.py`)

Deepfire cannot simulate 23 July, so the replay extrapolates from the hotspots themselves (the fallback in PLAN.md):

1. The last 6 hours of hotspots, split into two 3-hour halves, with isolated detections dropped (fewer than 2 others within 2 km).
2. **Direction:** from the older half's centroid to the recent half's. **Speed:** how far the leading edge (90th percentile along that direction) moved, per hour.
3. **Cone:** the leading edge swept forward speed × t, fanning ±25°, plus the burned area. One polygon per hour, up to 6 h.
4. **Time to impact** for a zone: the first 10-minute step at which the cone touches it (binary search); 0 if already burned; null if the cone does not reach it within 6 h.

On 23 July the front runs east-north-east (about 75°) at 1.5–2.4 km/h through the afternoon. **La Atalaya is first flagged at 14:00 UTC (16:00 CEST) with about 5 h to impact**; at the default scenario time (18:30 UTC) it is about 2 h 10 min away. These are the raw inputs for the lead time (#5). It is a heuristic with no wind or terrain, and it says so wherever it is shown.

Zones come from OpenStreetMap (`pnpm data:zones` → `data/zones.geojson`): 85 settlements, 12 care homes, 21 schools and 16 health centres in the demo box, as circles sized by kind. Risk is computed in 15-minute steps and cached. `GET /api/spread?at=`, `GET /api/zones/risk?at=` and `GET /api/zones` feed the dashboard; `get_fire_status` answers at the scenario time.

### Spread simulation (live mode only)

`POST /v1/fire-spread/simulations` with `clusterId` or `latitude`/`longitude`, and `durationHours` (1–24). Optional: `model` (`elmfire` default, or `forefire`), `ensembleMembers` (1–50), `sources`, `lookbackHours` (1–168, default 24).

It answers `202` with a `Location` header. Poll `GET /v1/fire-spread/simulations/{id}` about every 10 s until `COMPLETED`, `NO_SPREAD` or `FAILED`. The result is a GeoJSON FeatureCollection with one cumulative MultiPolygon per hour (`hour`, `elapsed_seconds`, and `burn_probability` for ensembles).

**There is no start-time parameter**: a simulation starts from the latest observations, and `lookbackHours` counts back from now. See [the finding](../findings/2026-09-19-deepfire-no-historical-simulation.md) before planning the 23 July replay around it.

## In Claude Code

The `deepfire` MCP server is in `.mcp.json` (no token). It searches *reported fires* (`deepfire_search_fires`, `deepfire_get_fire`); it does not serve raw hotspots or spread runs. It lists the Burgohondo fire only from 27 July, under an El Barraco place name (#3).

## Gotchas

- **30-second cap per query**: longer queries fail with HTTP 500. If a 3-hour window times out, shorten `WINDOW` in `fetch_hotspots.py`.
- **10,000 features per response**, and `sortby` is ignored, so walk time windows.
- **503 with `ogc-busy` and `Retry-After`** under load: shared capacity. This is why the demo reads from `data/`.
- **Two simulations in flight** per API client; a third gets 429 `too-many-simulations`.
- `FAILED` can mean the fire is "outside the modelled regions".

## Sources

- https://docs.deepfire.co/llms.txt · https://docs.deepfire.co/llms-full.txt
- Authentication: https://docs.deepfire.co/guides/authentication
- Fire spread: https://docs.deepfire.co/api/fire-spread · https://docs.deepfire.co/reference/fire-spread/simulations/create-simulation
- Limits: https://docs.deepfire.co/guides/performance-and-limits
- MCP: https://docs.deepfire.co/ai/connect-to-ai
