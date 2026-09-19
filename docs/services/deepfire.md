# Deepfire

**Used for:** step 1 (hotspots, live fires) and step 2 (predicted spread). Slices 2, 3 and 10 (#3, #4, #11).
**Status:** hotspots working (7,068 cached for the replay, `GET /api/hotspots`); live mode working (`GET /api/live/fires`), with its predicted spread from Deepfire's own automatic ELMFIRE runs (`GET /api/live/spread`) and, for a selected fire, its places at risk, alert drafts and roads to close (`GET /api/live/operations/{fire_id}`); replay spread done with our own cone, not with this API (see below)
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
| Spread runs | `GET /v1/fire-spread/simulations?since=…&limit=100`, then `cursor=<nextCursor>` | Live mode reads these; newest first, no `result` in list items |
| One run | `GET /v1/fire-spread/simulations/{id}` (the item's `links.self`) | `result`: the hourly polygons |
| New run | `POST /v1/fire-spread/simulations` | See below. We never call it |

Download the replay data once and commit it:

```bash
pnpm data:hotspots     # writes data/hotspots_2026-07-22_24.geojson
```

First run on 2026-09-19: about a minute, 7,068 hotspots, one cluster, no 3-hour window near the cap. The pipeline keeps only what the replay needs (`observed_at`, `fire_radiative_power`, `confidence`, `source`, `cluster_id`), rounds coordinates to 5 decimals and sorts by time: 2.2 MB on disk, ~250 KB gzipped over the wire. Sources: MTG (geostationary, every 10 minutes) 62%, VIIRS 29%, MODIS 5%, Sentinel-3 5%.

### Live mode

`backend/app/live.py` asks for active clusters (`filter=active = true`) over `-9.6,35.8,4.4,44.0`, which covers Iberia plus bits of southern France and northern Algeria. Clusters are bare points: `id`, `first_observed`, `last_observed`, `active`, with no country and no name. On 2026-09-19 at 16:17 CEST there were 116, returned in 0.6 s.

The backend caches the answer for 60 s and reuses one token for the life of the process. If Deepfire fails, it serves the last good answer marked `stale: true`; with nothing cached, it returns a 503, which the dashboard shows as a message. The dashboard polls every 60 s, only while live mode is on.

### Spread simulation

`POST /v1/fire-spread/simulations` with `clusterId` or `latitude`/`longitude`, and `durationHours` (1–24). Optional: `model` (`elmfire` default, or `forefire`), `ensembleMembers` (1–50), `sources`, `lookbackHours` (1–168, default 24).

It answers `202` with a `Location` header. Poll `GET /v1/fire-spread/simulations/{id}` about every 10 s until `COMPLETED`, `NO_SPREAD` or `FAILED`. The result is a GeoJSON FeatureCollection with one cumulative MultiPolygon per hour (`hour`, `elapsed_seconds`, and `burn_probability` for ensembles).

**The replay does not use it.** The 23 July spread in `data/spread_2026-07-23.geojson` is our own cone from the front's velocity (`backend/app/spread.py`, [the finding](../findings/2026-09-19-spread-cone-model.md)). No Deepfire run of that fire exists (see below).

### Live mode's predicted spread

Deepfire runs ELMFIRE by itself on active fires (`auto: true`): a physics model of terrain, fuel and weather. Live mode shows those runs and never queues one, so it spends none of the two-in-flight allowance.

`backend/app/live_spread.py`, served at `GET /api/live/spread`:

1. List the runs of the last 24 hours (`GET /v1/fire-spread/simulations?since=…`, at most 3 pages of 100).
2. Give each active fire from `GET /api/live/fires` the latest `COMPLETED` run whose ignition point is within 3 km of it. List items have no cluster id, and their `fireId` names a reported fire, not a cluster (none of 12 matched a cluster id), so the match is by distance. The one run checked in full carried a `clusterId` equal to the nearest cluster.
3. Fetch each matched run once (`GET /v1/fire-spread/simulations/{id}`, six at a time): a completed run never changes.
4. Answer with, per fire: the cluster id, name, run time, model, duration, burned area and the hourly polygons, largest first.

The answer is cached in memory for 5 minutes. The last good one is written to `data/live_spread.json` (not tracked, about 750 KB, 160 KB gzipped): when Deepfire fails, the backend serves it with `stale: true` and asks again after a minute; after a restart it also seeds the runs already fetched, so only new ones are downloaded. With nothing cached, the endpoint returns 503 and the dashboard shows the fires without spread. The dashboard polls every 5 minutes in live mode and draws each fire's hours with the replay's ramp (`SPREAD_HOUR_COLORS`), under the fire markers; a fire's popup names the run.

Verified against the live API on 2026-09-19 at about 20:40 CEST: 125 runs in the last 24 hours (114 `COMPLETED`, 11 `NO_SPREAD`), all `auto: true`, ELMFIRE, 12 h, one ensemble member, listed in two pages in 1.1 s. A run's detail is 6–7 KB with 12 hourly MultiPolygons (`hour`, `elapsed_seconds`, no `burn_probability`) and a `summary` (`burnedAreaM2`, `windSpeedAvgMs`, `windDirectionAvg`). 74 of the 141 active clusters matched a completed run; the first answer took 7 s, a refresh 0.5 s and a restart with the file 1.1 s.

### Live operations for one selected fire

Tap a live fire that has a run (or pick it from the list in the sheet) and the dashboard shows, for that fire only: the places at risk, their time to impact, alert drafts and the roads to close. `backend/app/live_operations.py`, served at `GET /api/live/operations/{fire_id}`:

1. **Places at risk.** The run's 12 h footprint plus 1,000 m (`BUFFER_M`) is sent to Overpass in one query: OSM place nodes (city, town, village, hamlet, suburb, quarter, neighbourhood, padded to 150–2,000 m by size), named `landuse=residential` (housing estates), and `fetch_zones`' care homes, schools, health centres and main roads (same selectors, same parsing). Roads are clipped to the search area. Footprints wider than 0.3° are cut into tiles; each request tries `OVERPASS_URL`, then the mirrors (`OVERPASS_MIRRORS`), for at most 30 s in total.
2. **Cache.** Per simulation id, in memory and in `data/live_places/<simulation id>.json` (git-ignored): a completed run never changes, so a second click is instant. If Overpass fails for a new run, the fire's last cached places come back with `places_stale: true`; with none, the endpoint returns 503. A Deepfire outage follows `/api/live/spread` (`spread_stale: true`, or 503).
3. **Time to impact.** For each place, the first hourly polygon that touches it (`impact.first_hour_touching`, shared with the replay): `minutes_from_run` from the run's start, `reaches_at`, and `minutes` left now (0 when due). Places inside the buffer that no hour reaches are listed apart, as near but not reached.
4. **Alert drafts.** One per reached place, soonest first, from `liveOps.*` in `backend/app/locales/`. They are drafts for the coordinator (`draft: true`, `sent: false`): nothing sends them, and the dashboard labels them "Draft, not sent".
5. **Roads to close.** Roads the run reaches within 60 minutes of now, the replay's rule (`closedRoads`): closed to residents, crews still use them. The map draws them with the replay's dashed red cordon.

No resident is listed and no call is made in live mode: that needs a registry of who lives in these places. See [What works for a real fire](../demo/real-life.md).

Verified on 2026-09-19 at about 22:15 CEST with the Arcos de la Frontera (Cádiz) run from 16:47 CEST: 95 OSM elements from `overpass.openstreetmap.fr` in 1.0–2.4 s (`overpass-api.de` refused the connection, `overpass.kumi.systems` timed out), 18 places (3 towns or villages, 4 housing estates, 7 schools, 3 health centres, 1 road), 11 reached within 12 h, 10 alert drafts, the N-4 to close. A second request took 0.01 s from the cache.

**No run of the 23 July fire.** Checked 2026-09-19 around 21:20 CEST, paging with `cursor` through everything since 2026-07-20: runs go back to 2026-07-21 17:44 UTC, 3,111 in total, all `auto: true`, all ELMFIRE, 12 h. None was created between 22 and 26 July inside lat 40.1–40.7, lon −5.1 to −4.1, and none mentions Ávila, El Tiemblo, Burgohondo, La Atalaya or Navaluenga. The replay keeps our cone.

**There is no start-time parameter**: a simulation starts from the latest observations, and `lookbackHours` counts back from now. See [the finding](../findings/2026-09-19-deepfire-no-historical-simulation.md) before planning the 23 July replay around it.

## In Claude Code

The `deepfire` MCP server is in `.mcp.json` (no token). It searches *reported fires* (`deepfire_search_fires`, `deepfire_get_fire`); it does not serve raw hotspots or spread runs. It lists the Burgohondo fire only from 27 July, under an El Barraco place name (#3).

## Gotchas

- **30-second cap per query**: longer queries fail with HTTP 500. If a 3-hour window times out, shorten `WINDOW` in `fetch_hotspots.py`.
- **10,000 features per response**, and `sortby` is ignored, so walk time windows.
- **503 with `ogc-busy` and `Retry-After`** under load: shared capacity. This is why the demo reads from `data/`.
- **Two simulations in flight** per API client; a third gets 429 `too-many-simulations`.
- `FAILED` can mean the fire is "outside the modelled regions".
- A run's `fireId` is not a cluster id: match runs to clusters by position (or by `clusterId`, which only the full run carries, and not always).

## Sources

- https://docs.deepfire.co/llms.txt · https://docs.deepfire.co/llms-full.txt
- Authentication: https://docs.deepfire.co/guides/authentication
- Fire spread: https://docs.deepfire.co/api/fire-spread · https://docs.deepfire.co/reference/fire-spread/simulations/create-simulation · https://docs.deepfire.co/reference/fire-spread/simulations/list-simulations · https://docs.deepfire.co/reference/fire-spread/simulations/get-simulation
- Limits: https://docs.deepfire.co/guides/performance-and-limits
- MCP: https://docs.deepfire.co/ai/connect-to-ai
