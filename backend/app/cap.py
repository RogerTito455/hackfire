"""Live mode's alert drafts as one CAP 1.2 document, the format ES-Alert and EU-Alert systems exchange.

The Common Alerting Protocol (OASIS CAP 1.2, http://docs.oasis-open.org/emergency/cap/v1.2/) is what
a civil-protection alerting system takes in. HackFire writes its drafts in it so the coordinator can
hand them to Protección Civil as they are. It sends nothing: `status` is always Draft, never Actual,
and nothing here talks to any alerting system.

One <alert> per fire; one <info> per language in app/locales (the residents' language first); one
<area> per place a draft names, with the place's outline as polygons, or a circle for a point.
Pure: `document(operations, now)` turns live_operations.operations()' answer into XML.
"""

import math
import re
import xml.etree.ElementTree as ET
from datetime import UTC, datetime, timedelta

from shapely.geometry import shape

from . import i18n
from .config import settings
from .live_operations import alert_drafts

NAMESPACE = "urn:oasis:names:tc:emergency:cap:1.2"
SENDER = "hackfire"
# Draft only: HackFire never issues a real (Actual) alert.
STATUS = "Draft"
# A place the simulation reaches within this many minutes makes the alert Immediate, else Expected.
IMMEDIATE_WITHIN_MIN = 60
# Outlines are simplified to about 50 m and a point gets a circle this wide.
SIMPLIFY_DEG = 0.0005
POINT_RADIUS_KM = 0.2
COORDINATE_DECIMALS = 5

ET.register_namespace("", NAMESPACE)


def cap_time(moment: datetime) -> str:
    """CAP's dateTime: seconds and an explicit offset, UTC written -00:00 (never Z)."""
    return moment.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%S-00:00")


def _identifier(operations: dict, now: datetime) -> str:
    raw = f"{SENDER}-{operations['fire_id']}-{operations['simulation_id']}-{now.astimezone(UTC):%Y%m%dT%H%M%S}"
    return re.sub(r"[^A-Za-z0-9._-]", "_", raw)


def _pairs(coordinates) -> str:
    return " ".join(f"{lat:.{COORDINATE_DECIMALS}f},{lon:.{COORDINATE_DECIMALS}f}" for lon, lat, *_ in coordinates)


def area_shapes(geometry: dict) -> tuple[list[str], list[str]]:
    """A place's GeoJSON geometry as CAP polygons ("lat,lon …", closed) and circles ("lat,lon km")."""
    outline = shape(geometry)
    if outline.is_empty:
        return [], []
    if outline.geom_type in ("Polygon", "MultiPolygon"):
        simple = outline.simplify(SIMPLIFY_DEG, preserve_topology=True)
        parts = list(getattr(simple, "geoms", [simple]))
        return [_pairs(part.exterior.coords) for part in parts if len(part.exterior.coords) >= 4], []
    if outline.geom_type == "Point":
        return [], [f"{outline.y:.{COORDINATE_DECIMALS}f},{outline.x:.{COORDINATE_DECIMALS}f} {POINT_RADIUS_KM}"]
    # A line or a collection: a circle around it.
    west, south, east, north = outline.bounds
    centre = outline.centroid
    half_diagonal_km = math.hypot((east - west) * 111.32 * math.cos(math.radians(centre.y)), (north - south) * 111.32) / 2
    radius = max(POINT_RADIUS_KM, round(half_diagonal_km, 2))
    return [], [f"{centre.y:.{COORDINATE_DECIMALS}f},{centre.x:.{COORDINATE_DECIMALS}f} {radius}"]


def locales() -> list[str]:
    """Every backend locale, the residents' language first."""
    return sorted(i18n.catalogue(), key=lambda code: (code != i18n.resolve(settings.resident_locale), code))


def _sub(parent: ET.Element, tag: str, text: str | None = None) -> ET.Element:
    element = ET.SubElement(parent, f"{{{NAMESPACE}}}{tag}")
    if text is not None:
        element.text = text
    return element


def _info(alert: ET.Element, operations: dict, locale: str, drafted: list[dict], expires: datetime | None) -> None:
    drafts = alert_drafts(drafted, locale)
    soonest = min(draft["minutes"] for draft in drafts)
    names = [draft["place"] for draft in drafts]
    info = _sub(alert, "info")
    _sub(info, "language", i18n.t("cap.language", locale))
    _sub(info, "category", "Fire")
    _sub(info, "event", i18n.t("cap.event", locale))
    _sub(info, "urgency", "Immediate" if soonest < IMMEDIATE_WITHIN_MIN else "Expected")
    _sub(info, "severity", "Severe")
    _sub(info, "certainty", "Likely")
    if expires is not None:
        _sub(info, "expires", cap_time(expires))
    _sub(info, "senderName", i18n.t("cap.senderName", locale))
    if len(names) == 1:
        headline = i18n.t("cap.headline", locale, place=names[0])
    else:
        headline = i18n.t("cap.headlineMany", locale, place=names[0], count=len(names) - 1)
    _sub(info, "headline", headline)
    run_at = datetime.fromisoformat(operations["run_at"].replace("Z", "+00:00"))
    intro = i18n.t("cap.description", locale, time=f"{run_at.astimezone(UTC):%Y-%m-%d %H:%M} UTC", model=operations["model"].upper())
    _sub(info, "description", "\n".join([intro, *(draft["text"] for draft in drafts)]))
    _sub(info, "instruction", i18n.t("cap.instruction", locale))
    for place, draft in zip(drafted, drafts, strict=True):
        polygons, circles = area_shapes(place["geometry"])
        area = _sub(info, "area")
        _sub(area, "areaDesc", draft["place"])
        for polygon in polygons:
            _sub(area, "polygon", polygon)
        for circle in circles:
            _sub(area, "circle", circle)


def drafted_places(operations: dict) -> list[dict]:
    """The places an alert draft names: reached, not roads, soonest first (live_operations' order)."""
    return [place for place in operations["places"] if place["kind"] != "road" and place["minutes"] is not None]


def document(operations: dict, now: datetime | None = None) -> bytes:
    """The fire's alert drafts as one CAP 1.2 <alert>, status Draft. Raises ValueError with no drafts."""
    drafted = drafted_places(operations)
    if not drafted:
        raise ValueError("no alert drafts for this fire")
    now = now or datetime.now(UTC)
    alert = ET.Element(f"{{{NAMESPACE}}}alert")
    _sub(alert, "identifier", _identifier(operations, now))
    _sub(alert, "sender", SENDER)
    _sub(alert, "sent", cap_time(now))
    _sub(alert, "status", STATUS)
    _sub(alert, "msgType", "Alert")
    _sub(alert, "scope", "Public")
    _sub(alert, "note", " / ".join(i18n.t("cap.note", locale) for locale in locales()))
    _sub(alert, "incidents", re.sub(r"\s+", "_", operations["fire_id"]))
    run_at = datetime.fromisoformat(operations["run_at"].replace("Z", "+00:00"))
    hours = operations.get("duration_hours")
    expires = run_at + timedelta(hours=hours) if hours else None
    for locale in locales():
        _info(alert, operations, locale, drafted, expires)
    ET.indent(alert)
    return ET.tostring(alert, encoding="utf-8", xml_declaration=True)
