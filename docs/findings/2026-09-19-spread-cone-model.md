# The replay spread is a cone from the front's velocity, and how it behaves on 23 July

**Date:** 2026-09-19 · **Area:** predicted spread, slice 3 (#4)

## What happened

The Deepfire simulation cannot replay a past date ([finding](2026-09-19-deepfire-no-historical-simulation.md)), and no answer from the Deepfire mentors is on record, so the replay uses the fallback in PLAN.md: `backend/app/spread.py` estimates the front's velocity from the last hours of satellite hotspots and projects the footprint forward. `pnpm data:spread` issues a forecast every 30 minutes of 23 July (UTC), each with a polygon for now and one per hour ahead up to 6 h.

**How it works.** The last 3 hours of hotspots are split in two halves. The heading is the displacement of the centroid from the earlier half to the recent half. The speed is how far the leading edge (90th percentile along the heading) advanced between the halves, clamped to 1–6 km/h. The footprint is the convex hull of the recent half, padded by 0.4 km; hour *h* is that footprint swept `speed × h` along the heading, with 30% of that distance spread to the flanks and backwards. Only hotspots observed at or before the issue time are used.

**Two things the raw estimate got wrong on the real data, both fixed:**

1. **The front's speed collapsed at 16:00 UTC and La Atalaya was un-flagged** while the front was still about 9 km away. From 15:30 to 18:00 UTC the data has almost no hotspots (hour 15 has 39, all MODIS; hours 16 and 17 have none) and the sensor mix changes, so one 3-hour window is noisy. The speed is now the strongest estimate of the last 3 hours, taken every 30 minutes and losing 10% per step of age. And a forecast stays valid for 3 hours, with its minutes counting down, so a gap in the data does not un-flag a zone.
2. **A floor of 0.5 km/h let a stalled but burning front read as safe** in the evening. The floor is now 1 km/h. This is a deliberate bias to over-warn: it can flag a zone that the fire then does not reach.

## What the forecasts say

Hours ahead at which the predicted spread first touches each place, by forecast issue time (UTC), from the committed `data/spread_2026-07-23.geojson`:

| Issued | La Atalaya | El Tiemblo | Estimated speed |
|---|---|---|---|
| 13:00 | not reached | not reached | 1.4 km/h |
| 13:30 | 5 h | 3 h | 3.0 km/h |
| 14:00 | 4 h | 2 h | 3.7 km/h |
| 15:00 | 4 h | 2 h | 3.4 km/h |
| 17:00 | 5 h | 2 h | 2.6 km/h |
| 18:30 | already inside the footprint | already inside | 1.9 km/h |
| 20:30 | 4 h | already inside | 1.0 km/h |

The first forecast that flags La Atalaya is the one issued at **13:30 UTC (15:30 local)**. The lead time is not computed here: it belongs to slice 4 (#5) and needs the definition of "reached" chosen in [the La Atalaya finding](2026-09-19-la-atalaya-location.md). From the 18:30 forecast on, La Atalaya is inside the footprint because the footprint is a hull around hotspots that include isolated ones east of the estate (longitude up to -4.404), not because a hotspot lies within the estate.

## Caveats

- **Not validated.** Nothing compares the cone with where the hotspots actually went. That is the IoU-style check of extension 3 (Devin, #19).
- **Many zones at once.** Over a 6-hour horizon, 56 of the 68 zones are at risk at some moment of the day, and 45 at 15:00 UTC. The panel shows the eight soonest and folds the rest.
- **Resolution is one hour.** Time to impact is `hours × 60` minus the age of the forecast, so it is exact only to the hour of the polygon that touches the zone.
- **The cone is a convex hull**, so it fills concavities between scattered hotspots and can cover places the fire never touched, such as the Navaluenga facilities on the west side, which show as "now" from 15:00 UTC.

## What we do about it

- Say "predicted fire area", never "the fire is at", in anything a resident hears. The `get_fire_status` summary already does.
- If the Deepfire mentors can produce a spread for 23 July, replace `spread.py`'s output with it; the file format and everything downstream stay the same.
- Tuning constants are at the top of `backend/app/spread.py`, each with the reason for its value.

## Sources

- `data/hotspots_2026-07-22_24.geojson`, `data/spread_2026-07-23.geojson`, `data/zones.geojson`
- `backend/tests/test_spread.py`, `backend/tests/test_fire_status.py`
