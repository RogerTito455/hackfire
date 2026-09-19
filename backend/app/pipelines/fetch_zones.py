"""Download the places the fire can reach from OpenStreetMap and cache them as static GeoJSON.

    pnpm data:zones

Needs no key. Writes data/zones.geojson: La Atalaya and El Tiemblo (ids `la-atalaya` and
`el-tiemblo`, the zones the resident registry refers to), care homes, schools, health centres and
main roads inside the demo box. Every zone is a polygon or a line, so it can be intersected with
the predicted spread.
"""

import json
import re
import sys
from dataclasses import dataclass

import httpx
import shapely
from shapely import LineString, MultiLineString, Point, Polygon
from shapely.geometry import mapping
from shapely.ops import unary_union

from ..config import DATA_DIR
from ..providers import overpass
from ..replay import DEMO_BOX

OUTPUT = DATA_DIR / "zones.geojson"

# The demo box as Overpass wants it: south, west, north, east.
BBOX_OVERPASS = "40.30,-4.85,40.50,-4.40"

# A facility mapped as a point is padded to roughly a building plot (about 150 m).
POINT_PADDING_DEG = 0.0015
# Roads are simplified to about 20 m: enough to say which road is cut, small enough to ship.
ROAD_TOLERANCE_DEG = 0.0002
COORDINATE_GRID_DEG = 0.00001  # about 1 m


@dataclass(frozen=True)
class Place:
    id: str
    name: str
    kind: str
    lon: float
    lat: float
    # OSM has no boundary for these: take the residential land use around the place's node.
    radius_m: int


# La Atalaya: hamlet node 1433078707. El Tiemblo: village node 64835850.
PLACES = [
    Place("la-atalaya", "La Atalaya", "estate", -4.46095, 40.3821, 1000),
    Place("el-tiemblo", "El Tiemblo", "town", -4.499, 40.413, 1500),
]

FACILITIES_QUERY = f"""
[out:json][timeout:90];
(
  nwr["amenity"~"^(nursing_home|school|kindergarten|clinic|hospital|doctors)$"]({BBOX_OVERPASS});
  nwr["social_facility"]({BBOX_OVERPASS});
);
out geom center tags;
"""

ROADS_QUERY = f"""
[out:json][timeout:90];
way["highway"~"^(trunk|primary|secondary)$"]["ref"]({BBOX_OVERPASS});
out geom tags;
"""


def residential_query(place: Place) -> str:
    return f"""
[out:json][timeout:60];
way["landuse"="residential"](around:{place.radius_m},{place.lat},{place.lon});
out geom tags;
"""


def facility_kind(tags: dict[str, str]) -> str | None:
    amenity = tags.get("amenity")
    if (
        amenity == "nursing_home"
        or tags.get("social_facility") in {"nursing_home", "assisted_living", "group_home"}
        or "residencia" in tags.get("name", "").lower()
    ):
        return "care_home"
    if amenity in {"school", "kindergarten"}:
        return "school"
    if amenity in {"clinic", "hospital", "doctors"}:
        return "health_centre"
    return None


def way_polygon(element: dict) -> Polygon | None:
    coords = [(p["lon"], p["lat"]) for p in element.get("geometry", [])]
    if len(coords) < 4 or coords[0] != coords[-1]:
        return None
    polygon = Polygon(coords)
    return polygon if polygon.is_valid else polygon.buffer(0)


def facility_geometry(element: dict) -> Polygon | None:
    """The building outline when OSM has one, otherwise a plot-sized square around the point."""
    if element["type"] == "way" and (polygon := way_polygon(element)) is not None:
        return polygon
    point = element.get("center") or element
    if "lon" not in point:
        return None
    return Point(point["lon"], point["lat"]).buffer(POINT_PADDING_DEG, quad_segs=2)


def finish(geometry, simplify: float = 0.0):
    """Clip to the demo box, simplify and snap coordinates to a ~1 m grid."""
    clipped = geometry.intersection(DEMO_BOX)
    if clipped.is_empty:
        return None
    if simplify:
        clipped = clipped.simplify(simplify, preserve_topology=True)
    return shapely.set_precision(clipped, COORDINATE_GRID_DEG)


def feature(zone_id: str, name: str | None, kind: str, osm: str | None, geometry) -> dict:
    return {
        "type": "Feature",
        "id": zone_id,
        "geometry": mapping(geometry),
        "properties": {"id": zone_id, "name": name, "kind": kind, "osm": osm},
    }


def place_features(client: httpx.Client) -> list[dict]:
    features = []
    for place in PLACES:
        polygons = [p for e in overpass.elements(client, residential_query(place)) if (p := way_polygon(e))]
        if not polygons:
            sys.exit(f"No residential land use within {place.radius_m} m of {place.name}")
        geometry = finish(unary_union(polygons))
        features.append(feature(place.id, place.name, place.kind, None, geometry))
        print(f"{place.id}: {len(polygons)} residential polygons")
    return features


def facility_features(client: httpx.Client) -> list[dict]:
    features = []
    for element in overpass.elements(client, FACILITIES_QUERY):
        kind = facility_kind(element["tags"])
        geometry = facility_geometry(element) if kind else None
        geometry = finish(geometry) if geometry is not None else None
        if geometry is None:
            continue
        osm = f"{element['type']}/{element['id']}"
        zone_id = f"{kind.replace('_', '-')}-{element['type'][0]}{element['id']}"
        features.append(feature(zone_id, element["tags"].get("name"), kind, osm, geometry))
    return features


def road_features(client: httpx.Client) -> list[dict]:
    """One zone per road number: a road is cut as soon as the fire touches any stretch of it."""
    by_ref: dict[str, list[LineString]] = {}
    for element in overpass.elements(client, ROADS_QUERY):
        coords = [(p["lon"], p["lat"]) for p in element.get("geometry", [])]
        if len(coords) >= 2:
            by_ref.setdefault(element["tags"]["ref"], []).append(LineString(coords))
    features = []
    for ref, lines in by_ref.items():
        geometry = finish(MultiLineString(lines), simplify=ROAD_TOLERANCE_DEG)
        if geometry is not None:
            features.append(feature(f"road-{re.sub(r'[^a-z0-9]+', '-', ref.lower()).strip('-')}", ref, "road", None, geometry))
    return features


def main() -> None:
    with httpx.Client(timeout=120) as client:
        features = place_features(client) + facility_features(client) + road_features(client)

    # Stable order so the file diffs cleanly: named places first, then by kind and id.
    features.sort(key=lambda f: (f["properties"]["kind"] not in {"estate", "town"}, f["properties"]["kind"], f["id"]))
    OUTPUT.write_text(
        json.dumps({"type": "FeatureCollection", "features": features}, separators=(",", ":")),
        encoding="utf-8",
    )
    kinds: dict[str, int] = {}
    for f in features:
        kinds[f["properties"]["kind"]] = kinds.get(f["properties"]["kind"], 0) + 1
    print(f"wrote {len(features)} zones {kinds} to {OUTPUT}")


if __name__ == "__main__":
    main()
