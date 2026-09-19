# Overpass (OpenStreetMap)

**Used for:** step 2, the zones the fire can reach. Slice 3 (#4).
**Status:** working; `data/zones.geojson` is cached and committed
**Owner:** whoever owns slice 3 (#4)

## Access

None: the Overpass API is public and keyless. Optionally set `OVERPASS_URL` in `.env` to use another instance (see Gotchas).

## In the app

`backend/app/providers/overpass.py` posts one Overpass QL query and returns its elements. `backend/app/pipelines/fetch_zones.py` builds the queries and writes the zones:

```bash
pnpm data:zones     # writes data/zones.geojson (68 zones, 63 KB), served at GET /api/zones
```

| Zone | Query | Geometry |
|---|---|---|
| `la-atalaya` (estate), `el-tiemblo` (town) | `landuse=residential` ways within 1,000 m of the La Atalaya hamlet node, 1,500 m of the El Tiemblo village node | The union of those outlines |
| Care homes | `amenity=nursing_home`, `social_facility` of `nursing_home`, `assisted_living` or `group_home`, or "Residencia" in the name | Building outline, or a ~150 m square around a point |
| Schools | `amenity=school` or `kindergarten` | Same |
| Health centres | `amenity=clinic`, `hospital` or `doctors` | Same |
| Main roads | `highway=trunk`, `primary` or `secondary` with a `ref`, one zone per road number | Lines simplified to ~20 m |

Everything is clipped to the demo box. Pharmacies, day centres and colleges are left out on purpose.

## Gotchas

- **Public instances come and go.** On 2026-09-19 `overpass-api.de` and several mirrors refused connections from one team machine, one mirror returned 504 on a one-node query, and `https://overpass.openstreetmap.fr/api/interpreter` worked. Set `OVERPASS_URL` to whichever answers. The file is committed, so the demo never depends on this.
- OSM tags are uneven: one school has no name, and unnamed zones are shown by their kind.

## Sources

- https://wiki.openstreetmap.org/wiki/Overpass_API
- https://overpass-turbo.eu (to try a query in the browser)
