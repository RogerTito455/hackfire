# Deepfire

**Used for:** step 1 (hotspots, live fires) and step 2 (predicted spread). Slices 2, 3 and 10 (#3, #4, #11).
**Status:** provider and hotspot pipeline written, not yet run against the API
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

### Spread simulation

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
