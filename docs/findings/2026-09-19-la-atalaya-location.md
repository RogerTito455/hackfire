# Where La Atalaya is, and how close the hotspots get

**Date:** 2026-09-19 · **Area:** replay data, slices 3 and 4 (#4, #5), registry (#12)

## What happened

1. **The sample registry put La Atalaya 7 km off.** Its three La Atalaya residents sat at about 40.431, -4.520, next to the El Burguillo reservoir. OpenStreetMap places the housing estate at **40.382, -4.461** (hamlet node 1433078707, "La Atalaya", El Tiemblo), confirmed by the bus stops "El Tiemblo - Urb. La Atalaya" at 40.383, -4.453. A different "La Atalaya" locality exists 15 km west (40.366, -4.644); do not confuse them.
2. **The replay data** (`pnpm data:hotspots`, 22–24 July 2026, box `-4.85,40.30,-4.40,40.50`): 7,068 hotspots, all in one Deepfire cluster, first at 22 July 11:08 UTC, last at 24 July 22:15 UTC.
3. **The nearest hotspot to the estate point, by hour on 23 July (UTC):** 18.3 km at 07:00, 14.1 km at 12:00, 9.0 km at 14:00, 4.9 km at 18:00, **3.0 km at 19:00 and 20:00**, 2.8 km at 21:00. No hotspot falls within 1 km of the point in the whole replay; the closest is 1.9 km (MODIS, 24 July 21:12 UTC).

Spain is UTC+2 in July, so 19:00 UTC is 21:00 local time.

## Why it matters

- **The lead time (#5) depends on the definition of "the fire reached La Atalaya".** With a point and a 1 km radius it never happens; with 3 km it happens on 23 July at about 19:00 UTC. Satellite pixels are 375 m (VIIRS) to about 1–2 km (MODIS, MTG), so a radius of a few kilometres, or the estate's polygon buffered by the pixel size, is defensible. Choose it once, write it in the pitch notes, and apply it both to "flagged" and to "reached". **Chosen in #5: a hotspot within 3 km of the estate's outline, see [the lead-time finding](2026-09-19-lead-time.md).** (The polygon in `zones.geojson` is the estate's own outline, not a radius; the predicted spread carries its own padding, see [the spread finding](2026-09-19-spread-cone-model.md).)
- ~~OSM has no polygon for the estate, only the hamlet node and the bus stops.~~ **Corrected while building #4:** OSM does have it as `landuse=residential` polygons: way 28159561 (centred at 40.381, -4.461, 131 points) and way 198306680 (40.388, -4.464), both within 1 km of the hamlet node. `zones.geojson` uses them, about 0.7 km² in all, so no buffer around the node is needed.
- The scattered hotspots away from the front are few: 17 of 7,068 have at most one neighbour within 1.5 km, mostly Sentinel-3B. They are left in; the replay shows the data as Deepfire serves it.

## What we did

- `data/neighbors.sample.json`: the three La Atalaya residents now sit inside the estate. The real registry (#12, `neighbors.local.json`) needs real addresses there too.
- `backend/tests/test_replay.py` checks that the replay has hotspots within 5 km of the estate on 23 July.

## Sources

- https://www.openstreetmap.org/node/1433078707
- Overpass query for `name~"Atalaya"` in the demo box, run 2026-09-19
- `data/hotspots_2026-07-22_24.geojson`
