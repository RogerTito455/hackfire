"""Download the places the fire could reach from OpenStreetMap and cache them as data/zones.geojson.

    pnpm data:zones

Settlements (towns, villages, hamlets, housing estates) and vulnerable places (care homes, schools,
health centres) in the demo box. OSM mostly has points for them, so each zone is a circle whose
radius depends on the kind of place. The ids la-atalaya and el-tiemblo match the registry.

The public Overpass servers time out on big queries, so the box is asked for in tiles. If every
mirror is down, save an Overpass [out:json] answer by hand and pass it instead:

    cd backend && uv run python -m app.pipelines.fetch_zones path/to/overpass.json
"""

import json
import re
import sys
import time
import unicodedata
from pathlib import Path

import shapely
from shapely.geometry import Point, mapping

from .. import geo
from ..config import DATA_DIR
from ..providers import overpass

OUTPUT = DATA_DIR / "zones.geojson"
BBOX = (40.30, -4.85, 40.50, -4.40)  # south, west, north, east

# Zone radius in metres by OSM tag value.
RADIUS_M = {"town": 1_500, "village": 1_000, "hamlet": 500, "suburb": 500, "neighbourhood": 400}
FACILITY_RADIUS_M = 150
FACILITY_KIND = {
    "nursing_home": "care_home",
    "social_facility": "care_home",
    "school": "school",
    "hospital": "health",
    "clinic": "health",
    "doctors": "health",
}


def slug(name: str) -> str:
    ascii_name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", ascii_name.lower()).strip("-")


def zone(element: dict, kind: str, radius: float) -> dict:
    lat = element.get("lat") or element["center"]["lat"]
    lon = element.get("lon") or element["center"]["lon"]
    circle = Point(geo.point_m(lon, lat)).buffer(radius, quad_segs=8)
    return {
        "type": "Feature",
        "id": slug(element["tags"]["name"]),
        "geometry": mapping(shapely.set_precision(geo.to_degrees(circle), 1e-5)),
        "properties": {
            "name": element["tags"]["name"],
            "kind": kind,
            "osm": f"{element['type']}/{element['id']}",
            "lat": round(lat, 5),
            "lon": round(lon, 5),
        },
    }


def download(tiles: int = 3) -> list[dict]:
    """Ask Overpass tile by tile: one query for the whole box times out."""
    south, west, north, east = BBOX
    step = (east - west) / tiles
    elements: list[dict] = []
    for i in range(tiles):
        box = f"({south},{west + i * step},{north},{west + (i + 1) * step})"
        ql = (
            "[out:json][timeout:25];("
            f'node["place"~"^(town|village|hamlet|suburb|neighbourhood)$"]["name"]{box};'
            f'nwr["amenity"~"^(nursing_home|social_facility|school|hospital|clinic|doctors)$"]["name"]{box};'
            ");out center tags;"
        )
        for attempt in range(1, 5):
            try:
                elements += overpass.query(ql)
                break
            except RuntimeError as error:
                if attempt == 4:
                    raise
                print(f"tile {i + 1}: attempt {attempt} failed, retrying ({str(error).splitlines()[-1][:80]})")
                time.sleep(10 * attempt)
        print(f"tile {i + 1}/{tiles}: {len(elements)} elements so far")
    return elements


def main() -> None:
    if len(sys.argv) > 1:
        elements = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))["elements"]
    else:
        elements = download()
    features: dict[str, dict] = {}
    for element in elements:
        tags = element["tags"]
        if "place" in tags:
            feature = zone(element, "settlement", RADIUS_M[tags["place"]])
        else:
            feature = zone(element, FACILITY_KIND[tags["amenity"]], FACILITY_RADIUS_M)
        features.setdefault(feature["id"], feature)  # first wins on duplicate names
    ordered = sorted(features.values(), key=lambda f: (f["properties"]["kind"], f["id"]))
    OUTPUT.write_text(
        json.dumps({"type": "FeatureCollection", "features": ordered}, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    kinds = {k: sum(f["properties"]["kind"] == k for f in ordered) for k in sorted({f["properties"]["kind"] for f in ordered})}
    print(f"wrote {len(ordered)} zones to {OUTPUT}: {kinds}")


if __name__ == "__main__":
    main()
