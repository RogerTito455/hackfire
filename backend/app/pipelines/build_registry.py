"""Build the demo resident registry from OpenStreetMap addresses.

    pnpm data:registry

Needs no key. Writes the active scenario's tracked registry (HACKFIRE_SCENARIO; the demo's:
data/neighbors.sample.json) — never `neighbors.local.json`, which holds the team's real numbers.

For every named place of the scenario (the demo's: La Atalaya and El Tiemblo) it asks Overpass for
the addressed buildings inside the zone `pnpm data:zones` drew, and for the named residential streets
as a fallback where OSM has no house numbers (La Atalaya has none: the estate's streets are mapped,
its buildings are not). Households are then spread across the zone: each new one is placed as far as
possible from every household already chosen, so they do not cluster in one street.

Households are labelled by their street, as the registry has always been ("Hogar de la calle del
Júcar"), never with a person's name, and the phones stay the `+34000000001` placeholders. The zones
share the ten households in proportion to their area.

Residents already in the file keep their id, coordinates, name and phone, and count towards their
zone's share: the cached routes (`data/routes_cache.json`) are keyed by coordinates, and
`data/demo_timeline.json` names residents by their position. Delete the file to build one from
scratch.

Deterministic: no sampling, no randomness. The candidates are sorted and each household is the one
farthest from those already chosen, ties going to the first in that order, so the same OSM data
always gives the same file.
"""

import json
import re
import sys
import unicodedata
from dataclasses import dataclass

import httpx
from shapely.geometry import LineString, MultiPoint, Point, shape
from shapely.geometry.base import BaseGeometry
from shapely.ops import unary_union

from .. import geo
from ..providers import overpass
from ..scenario import NamedPlace, current

# Norma print() in production code: a command's stdout is its interface, not a log
# (app/pipelines/__init__.py).

HOUSEHOLDS = 10
# Overpass answers a whole-zone query slowly under load; this is the wait the download is given.
OVERPASS_TIMEOUT_SECONDS = 120
# The streets a household can live on when the zone has no addressed buildings.
STREET_TYPES = "residential|living_street|unclassified|pedestrian|tertiary"
# Household labels read "Hogar de la calle…" or "Hogar del paseo…" after the street's first word.
FEMININE = {"calle", "avenida", "travesia", "plaza", "carretera", "ronda", "urbanizacion", "colonia",
            "cuesta", "glorieta", "vereda", "senda", "bajada", "subida", "via"}
MASCULINE = {"paseo", "camino", "callejon", "pasaje", "barrio", "poligono", "parque", "puente", "sector"}


@dataclass(frozen=True)
class Household:
    """One line of the registry."""

    id: str
    name: str
    phone: str
    address: str
    zone: str
    lat: float
    lon: float

    def as_json(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "phone": self.phone,
            "address": self.address,
            "zone": self.zone,
            "lat": self.lat,
            "lon": self.lon,
        }


@dataclass(frozen=True)
class Candidate:
    """A place in a zone a household can be put at: a building with an address, or a street."""

    street: str
    number: str | None
    lon: float
    lat: float

    @property
    def order(self) -> tuple:
        """Sorted on before anything is chosen, so the result never depends on Overpass's order."""
        return (self.number is None, self.street, self.number or "", self.lon, self.lat)


def query(place: NamedPlace) -> str:
    """Addressed buildings and named streets around the place's node, in one query."""
    around = f"around:{place.radius_m},{place.lat},{place.lon}"
    return f"""
[out:json][timeout:90];
(
  nwr["addr:street"]({around});
  way["highway"~"^({STREET_TYPES})$"]["name"]({around});
);
out geom tags;
"""


def zone_shape(zone_id: str) -> BaseGeometry:
    """The zone `pnpm data:zones` drew, which a household has to be inside."""
    zones = json.loads(current().files.zones.read_text(encoding="utf-8"))
    for feature in zones["features"]:
        if feature["properties"]["id"] == zone_id:
            return shape(feature["geometry"])
    sys.exit(f"{zone_id} is not in {current().files.zones}: run `pnpm data:zones` first")


def middle(element: dict) -> Point | None:
    """Where a node sits, or the middle of the building a way draws."""
    if "lon" in element:
        return Point(element["lon"], element["lat"])
    points = [(p["lon"], p["lat"]) for p in element.get("geometry", [])]
    return MultiPoint(points).centroid if points else None


def addressed(element: dict, area: BaseGeometry) -> Candidate | None:
    """A building (or node) with a street address, at its centre, when it is inside the zone."""
    tags = element.get("tags", {})
    point = middle(element)
    if "addr:street" not in tags or point is None or not area.contains(point):
        return None
    number = (tags.get("addr:housenumber") or "").strip() or None
    return Candidate(tags["addr:street"].strip(), number, point.x, point.y)


def streets(elements: list[dict], area: BaseGeometry) -> list[Candidate]:
    """One candidate per named street, at the middle of the stretch that runs inside the zone."""
    lines: dict[str, list[LineString]] = {}
    for element in elements:
        name = element.get("tags", {}).get("name")
        points = [(p["lon"], p["lat"]) for p in element.get("geometry", [])]
        if not name or "highway" not in element.get("tags", {}) or len(points) < 2:
            continue
        inside = LineString(points).intersection(area)
        if not inside.is_empty:
            lines.setdefault(name.strip(), []).append(inside)
    candidates = []
    for name, stretches in lines.items():
        middle = unary_union(stretches).interpolate(0.5, normalized=True)
        candidates.append(Candidate(name, None, middle.x, middle.y))
    return candidates


def candidates(client: httpx.Client, place: NamedPlace) -> list[Candidate]:
    """Every place in the zone a household can be put at, the addressed buildings first."""
    elements = overpass.elements(client, query(place))
    area = zone_shape(place.id)
    buildings = [c for element in elements if (c := addressed(element, area))]
    return sorted(buildings + streets(elements, area), key=lambda c: c.order)


def shares(places: tuple[NamedPlace, ...], total: int, taken: dict[str, int]) -> dict[str, int]:
    """How many households each zone gets: its share of the total by area (largest remainder), and
    never fewer than it already has."""
    areas = {place.id: geo.to_metres(zone_shape(place.id)).area for place in places}
    whole = sum(areas.values())
    exact = {zone: area / whole * total for zone, area in areas.items()}
    given = {zone: max(int(value), taken.get(zone, 0)) for zone, value in exact.items()}
    # The remainders, biggest first, take what rounding down left over.
    left = total - sum(given.values())
    for zone in sorted(exact, key=lambda z: (-(exact[z] % 1), z))[: max(left, 0)]:
        given[zone] += 1
    return given


def spread_out(
    pool: list[Candidate], chosen: list[tuple[float, float]], used: set[str], how_many: int
) -> list[tuple[Candidate, bool]]:
    """`how_many` candidates, each the one farthest from everything chosen so far, and whether its
    street already had a household (then the label has to say which house it is). Pure.

    A street that already has a household is skipped while another street is free, so the households
    are spread across the zone's streets and not lined up along one of them.
    """
    points = [geo.point_m(lon, lat) for lon, lat in chosen]
    taken = set(used)
    picked: list[tuple[Candidate, bool]] = []
    for _ in range(how_many):
        free = [c for c in pool if c.street not in taken] or pool
        if not free:
            break
        farthest = max(free, key=lambda c: min((geo.point_m(c.lon, c.lat).distance(p) for p in points), default=0.0))
        picked.append((farthest, farthest.street in taken))
        pool = [c for c in pool if c is not farthest]
        points.append(geo.point_m(farthest.lon, farthest.lat))
        taken.add(farthest.street)
    return picked


def _plain(word: str) -> str:
    """Lower case without accents, for looking a street's first word up."""
    stripped = unicodedata.normalize("NFD", word.lower())
    return "".join(c for c in stripped if unicodedata.category(c) != "Mn")


def label(street: str, distinguish: str | None) -> str:
    """The household's name: "Hogar de la calle del Júcar", with the street's first word lowercased."""
    first, _, rest = street.partition(" ")
    kind = _plain(first)
    article = "de la" if kind in FEMININE else "del" if kind in MASCULINE else "de"
    name = f"Hogar {article} {first.lower()} {rest}".strip() if rest else f"Hogar {article} {street}"
    return f"{name} ({distinguish})" if distinguish else name


def street_of(address: str) -> str:
    """The street a registry address starts with, without its house number."""
    return re.sub(r"[\s,]+\d+\S*$", "", address.split(",")[0]).strip()


def household(index: int, candidate: Candidate, place: NamedPlace, repeated: bool) -> Household:
    """One resident: a placeholder phone, a label from the street and the zone's address ending."""
    number = f" {candidate.number}" if candidate.number else ""
    tail = place.address or place.name
    return Household(
        id=f"n{index:02d}",
        name=label(candidate.street, candidate.number if repeated else None),
        phone=f"+34{index:09d}",
        address=f"{candidate.street}{number}, {tail}",
        zone=place.id,
        lat=round(candidate.lat, 5),
        lon=round(candidate.lon, 5),
    )


def existing() -> list[Household]:
    """The registry as it stands, which keeps its ids, coordinates, names and phones."""
    path = current().files.registry
    if not path.exists():
        return []
    return [Household(**entry) for entry in json.loads(path.read_text(encoding="utf-8"))]


def build(client: httpx.Client, total: int) -> list[Household]:
    kept = existing()
    taken = {place.id: sum(1 for h in kept if h.zone == place.id) for place in current().places}
    quota = shares(current().places, total, taken)
    used = {street_of(h.address) for h in kept}
    chosen = [(h.lon, h.lat) for h in kept]
    households = list(kept)
    for place in current().places:
        wanted = quota[place.id] - taken.get(place.id, 0)
        print(f"{place.id}: {taken.get(place.id, 0)} already there, {wanted} to add")
        if wanted <= 0:
            continue
        pool = candidates(client, place)
        numbered = [c for c in pool if c.number]
        print(f"  {len(pool)} places to choose from ({len(numbered)} with a house number)")
        # A house number is the most accurate address a zone can give, so those go first; where OSM
        # has none (La Atalaya: its streets are mapped, its buildings are not) the street is it.
        added = 0
        for tier in (numbered, [c for c in pool if not c.number]):
            for candidate, repeated in spread_out(tier, chosen, used, wanted - added):
                households.append(household(len(households) + 1, candidate, place, repeated))
                chosen.append((candidate.lon, candidate.lat))
                used.add(candidate.street)
                added += 1
                print(f"  {households[-1].id} {households[-1].address}")
            if added >= wanted:
                break
    return households


def main() -> None:
    with httpx.Client(timeout=OVERPASS_TIMEOUT_SECONDS) as client:
        households = build(client, HOUSEHOLDS)
    output = current().files.registry
    output.write_text(
        json.dumps([h.as_json() for h in households], ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"wrote {len(households)} households to {output}")


if __name__ == "__main__":
    main()
