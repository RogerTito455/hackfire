# DGT (road incidents, DATEX II)

**Used for:** live mode (step 1 and the roads in step 4 of PLAN.md, for a real fire): the official forest-fire incidents on the map, and the official closures near a selected fire next to HackFire's own suggestions. Points 5 and 6 of [What works for a real fire](../demo/real-life.md).
**Status:** working (`GET /api/live/dgt`, and `dgt` in `GET /api/live/operations/{fire_id}`)
**Owner:** Bryan

## Access

None: the DGT (Dirección General de Tráfico, Spain's traffic authority) publishes its road incidents openly on the National Access Point, https://nap.dgt.es, with no key. `DGT_FEED_URL` (optional, see [environment](../setup/environment.md)) overrides the feed; empty means `https://nap.dgt.es/datex2/v3/dgt/SituationPublication/datex2_v36.xml`.

## In the app

`backend/app/providers/dgt.py` fetches and parses the feed with the standard library (`xml.etree`, no new dependency). `backend/app/live_dgt.py` keeps the records live mode uses and caches them.

| What | Where | Notes |
|---|---|---|
| The feed | `GET https://nap.dgt.es/datex2/v3/dgt/SituationPublication/datex2_v36.xml` | Redirects (followed) to `datex2_v37.xml`. DATEX II v3, `lang="es"`, profile "DGT (Spain) Profile RTTI SituationPublication" 3.7_1.0. About 3 MB, 0.5 s |
| Kept | Forest-fire incidents (`environmentalObstructionType` = `forestFire`) and closures (`roadOrCarriagewayOrLaneManagementType` = `roadClosed` or `carriagewayClosures`), `validityStatus` active | Lane closures, roadworks layouts and speed limits are left out |
| Whole of Spain | `GET /api/live/dgt` | `forest_fires` and `closures`, each record with `road`, `cause`, `cause_detail`, `management`, `since` (`overallStartTime`), `from` (and `to` for a stretch) with lat, lon, km point, municipality, province |
| Near one fire | `dgt` in `GET /api/live/operations/{fire_id}` | Records whose point or stretch touches the run's footprint plus 5 km (`NEAR_FIRE_M`), forest fires first. `available: false` when the DGT is down and nothing is cached; the rest of the answer never fails for it |

**Cache.** 5 minutes in memory. The last good answer is written to `data/live_dgt.json` (git-ignored, about 100 KB). When the DGT fails, it comes back with `stale: true` and the DGT is asked again after a minute; after a restart the file is the fallback. With nothing cached, `/api/live/dgt` returns 503. Timeout 10 s.

**On screen.** Live mode draws the forest-fire incidents as small navy warning triangles with a fire dot, unlike Deepfire's round fire markers, with a popup that names the DGT as the source. The selected fire's panel lists "Official DGT closures and incidents" under HackFire's own "Roads to close", with an "Official" badge, the road, km point, type, cause, municipality and since when, and the line "Source: DGT, National Access Point (DATEX II feed)".

### The record structure

Checked against the feed and its XSD (`https://nap.dgt.es/datex2/v3/dgt/SituationPublication/xsd/3.7_1.0/LevelC_3_D2Payload.xsd` and the files it includes) on 2026-09-19:

- `d2:payload` > `sit:situation id` > one or more `sit:situationRecord id version xsi:type` (432 situations had one record, one had nine).
- Record types: `RoadOrCarriagewayOrLaneManagement` (431), `GenericSituationRecord` (257), `SpeedManagement`, `NonWeatherRelatedRoadConditions`, `PoorEnvironmentConditions` and a few others.
- `sit:validity` > `com:validityStatus` (all `active`), `com:validityTimeSpecification` > `com:overallStartTime` and sometimes `overallEndTime`.
- `sit:cause` > `sit:causeType` and `sit:detailedCauseType` > for example `sit:environmentalObstructionType` (`forestFire`, `rockfalls`, `flooding`, `avalanches`) or `sit:roadMaintenanceType`.
- `sit:locationReference xsi:type`:
  - `loc:PointLocation` > `loc:tpegPointLocation` > `loc:point` > `loc:pointCoordinates` (`latitude`, `longitude`);
  - `loc:SingleRoadLinearLocation` > `loc:tpegLinearLocation` > `loc:from` and `loc:to`, each with coordinates.
  - Each point carries the DGT's Spanish extension: `lse:kilometerPoint`, `lse:municipality`, `lse:province`, `lse:autonomousCommunity`.
  - `loc:supplementaryPositionalDescription` > `loc:roadInformation` > `loc:roadName` (and sometimes `roadDestination`).
- Management types seen: `laneClosures` 138, `carriagewayClosures` 114, `roadClosed` 34, `singleAlternateLineTraffic` 28 and others.
- **No free text.** The schema allows `sit:generalPublicComment`, but the feed had none; the parser reads it if it appears.

Verified on 2026-09-19 at 22:26 CEST: 726 records in 555 situations, 3 active forest-fire records (FV-1 at La Oliva, Las Palmas, lanes closed since 3 September; A-1 at La Puebla de Arganzón, Burgos, lanes closed since 12:37; N-340 at Adra, Almería, carriageway closed since 21:04), and 148 road or carriageway closures. The backend fetched and parsed it in 0.5 s. With Deepfire's 75 simulated fires that evening, 6 had DGT closures within 5 km of their footprint (for example Marchena, Seville: the SE-225 closed and a carriageway of the A-8100 closed).

## In Claude Code

No MCP server.

## Gotchas

- **Official, but not about the fire.** Most closures near a fire are roadworks or damaged roads. The panel shows the cause, and forest-fire records come first.
- **The feed changes version.** The v36 URL redirects to v37; follow redirects and do not hard-code the target.
- **Timestamps carry their own offset** (`+01:00` or `+02:00`); the dashboard shows them in Spain's time zone.
- **Records may lack a stretch.** A point location has no `to`; a record with no coordinates at all is skipped.
- **Canary Islands.** Records there (FV-1) fall outside live mode's Iberian map box; they are still in `/api/live/dgt`.

## Sources

- National Access Point: https://nap.dgt.es
- The feed: https://nap.dgt.es/datex2/v3/dgt/SituationPublication/datex2_v36.xml
- Its schema: https://nap.dgt.es/datex2/v3/dgt/SituationPublication/xsd/3.7_1.0/LevelC_3_D2Payload.xsd
- DATEX II: https://www.datex2.eu
