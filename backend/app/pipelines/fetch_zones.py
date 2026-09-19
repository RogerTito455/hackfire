"""Download the places the fire can reach from OpenStreetMap and cache them as static GeoJSON.

    pnpm data:zones

Needs no key. Writes the active scenario's zones (HACKFIRE_SCENARIO; the demo's: data/zones.geojson):
the scenario's named places (the demo's: La Atalaya and El Tiemblo, ids `la-atalaya` and `el-tiemblo`,
the zones the resident registry refers to), care homes, schools, health centres and main roads inside
the scenario's box. Every zone is a polygon or a line, so it can be intersected with the predicted
spread.
"""

import json
import re
import sys

import httpx
import shapely
from shapely import LineString, MultiLineString, Point, Polygon
from shapely.geometry import mapping
from shapely.ops import unary_union

from ..providers import overpass
from ..scenario import NamedPlace as Place
from ..scenario import current

# A facility mapped as a point is padded to roughly a building plot (about 150 m).
POINT_PADDING_DEG = 0.0015
# Roads are simplified to about 20 m: enough to say which road is cut, small enough to ship.
ROAD_TOLERANCE_DEG = 0.0002
COORDINATE_GRID_DEG = 0.00001  # about 1 m



def overpass_bbox(bbox: tuple[float, float, float, float]) -> str:
    """The scenario's box as Overpass wants it: south, west, north, east."""
    west, south, east, north = bbox
    return ",".join(str(value) for value in (south, west, north, east))


def facilities_query(bbox: str) -> str:
    return f"""
[out:json][timeout:90];
(
  nwr["amenity"~"^(nursing_home|school|kindergarten|clinic|hospital|doctors)$"]({bbox});
  nwr["social_facility"]({bbox});
);
out geom center tags;
"""


def roads_query(bbox: str) -> str:
    return f"""
[out:json][timeout:90];
way["highway"~"^(trunk|primary|secondary)$"]["ref"]({bbox});
out geom tags;
"""


def residential_query(place: Place) -> str:
    """OSM has no boundary for the named places: take the residential land use around the node."""
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
    """Clip to the scenario's box, simplify and snap coordinates to a ~1 m grid."""
    clipped = geometry.intersection(current().box)
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
    for place in current().places:
        polygons = [p for e in overpass.elements(client, residential_query(place)) if (p := way_polygon(e))]
        if not polygons:
            sys.exit(f"No residential land use within {place.radius_m} m of {place.name}")
        geometry = finish(unary_union(polygons))
        features.append(feature(place.id, place.name, place.kind, None, geometry))
        print(f"{place.id}: {len(polygons)} residential polygons")
    return features


def facility_features(client: httpx.Client) -> list[dict]:
    features = []
    for element in overpass.elements(client, facilities_query(overpass_bbox(current().bbox))):
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
    for element in overpass.elements(client, roads_query(overpass_bbox(current().bbox))):
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
    output = current().files.zones
    output.write_text(
        json.dumps({"type": "FeatureCollection", "features": features}, separators=(",", ":")),
        encoding="utf-8",
    )
    kinds: dict[str, int] = {}
    for f in features:
        kinds[f["properties"]["kind"]] = kinds.get(f["properties"]["kind"], 0) + 1
    print(f"wrote {len(features)} zones {kinds} to {output}")


if __name__ == "__main__":
    main()
