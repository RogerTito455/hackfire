"""DGT (Spain's traffic authority): the road incidents it publishes on the National Access Point.

A public DATEX II v3 feed, no key: https://nap.dgt.es. `DGT_FEED_URL` (config.py) points at the
SituationPublication file, which redirects to the current version (datex2_v37.xml on 2026-09-19,
about 3 MB, some 700 situation records in Spanish). Parsed with the standard library.

Each record becomes a plain dict: its road, a point (and the far end for a stretch), its cause, how
the road is managed (roadClosed, carriagewayClosures, laneClosures…) and since when. Only the
official data is kept; nothing is inferred.
"""

import xml.etree.ElementTree as ET

import httpx

from ..config import settings

_HEADERS = {"User-Agent": "hackfire-hackbarna/0.1 (wildfire evacuation demo)"}

_SIT = "{http://levelC/schema/3/situation}"
_XSI_TYPE = "{http://www.w3.org/2001/XMLSchema-instance}type"

FOREST_FIRE = "forestFire"
# Management types that shut a road or a whole carriageway; lane closures keep traffic moving.
CLOSURE_TYPES = frozenset({"roadClosed", "carriagewayClosures"})


def ping(client: httpx.Client) -> int:
    """For the status page (app/provider_status.py): the feed's status code, without its 3 MB."""
    return client.head(settings.dgt_feed_url, headers=_HEADERS, follow_redirects=True).status_code


def fetch(client: httpx.Client) -> bytes:
    """The whole feed, following its redirect to the current version."""
    response = client.get(settings.dgt_feed_url, headers=_HEADERS, follow_redirects=True)
    response.raise_for_status()
    return response.content


def _local(element: ET.Element) -> str:
    return element.tag.rsplit("}", 1)[-1]


def _first(element: ET.Element | None, name: str) -> str | None:
    """The text of the first descendant called `name`, whatever its namespace."""
    if element is None:
        return None
    for child in element.iter():
        if _local(child) == name and child.text and child.text.strip():
            return child.text.strip()
    return None


def _child(element: ET.Element | None, name: str) -> ET.Element | None:
    if element is None:
        return None
    return next((child for child in element.iter() if _local(child) == name), None)


def _point(element: ET.Element | None) -> dict | None:
    """A TPEG point: coordinates plus the DGT's Spanish extension (km point, municipality…)."""
    lat, lon = _first(element, "latitude"), _first(element, "longitude")
    if lat is None or lon is None:
        return None
    try:
        point = {"lat": round(float(lat), 6), "lon": round(float(lon), 6)}
    except ValueError:
        return None
    km = _first(element, "kilometerPoint")
    point["km"] = float(km) if km is not None and km.replace(".", "", 1).isdigit() else None
    point["municipality"] = _first(element, "municipality")
    point["province"] = _first(element, "province")
    point["community"] = _first(element, "autonomousCommunity")
    return point


def _comments(record: ET.Element) -> list[str]:
    """generalPublicComment texts (in the schema; absent from the feed on 2026-09-19)."""
    texts = []
    for comment in record:
        if _local(comment) == "generalPublicComment":
            texts += [value.text.strip() for value in comment.iter() if _local(value) == "value" and value.text]
    return texts


def parse_record(record: ET.Element, situation_id: str | None) -> dict | None:
    """One situationRecord as a dict; None when it has no usable position."""
    location = record.find(f"{_SIT}locationReference")
    linear = _child(location, "tpegLinearLocation")
    if linear is not None:
        start, end = _point(_child(linear, "from")), _point(_child(linear, "to"))
    else:
        start, end = _point(_child(location, "tpegPointLocation")), None
    if start is None:
        start, end = end, None
    if start is None:
        return None
    cause = record.find(f"{_SIT}cause")
    detail = _child(cause, "detailedCauseType")
    detailed = next((child.text.strip() for child in (detail if detail is not None else []) if child.text), None)
    management = _first(record, "roadOrCarriagewayOrLaneManagementType")
    return {
        "id": record.get("id"),
        "situation_id": situation_id,
        "record_type": (record.get(_XSI_TYPE) or "").split(":")[-1] or None,
        "road": _first(location, "roadName"),
        "destination": _first(location, "roadDestination"),
        "direction": _first(location, "tpegDirection"),
        "cause": _first(cause, "causeType"),
        "cause_detail": detailed,
        "management": management,
        "forest_fire": detailed == FOREST_FIRE,
        "closure": management in CLOSURE_TYPES,
        "severity": _first(record, "severity"),
        "validity": _first(record.find(f"{_SIT}validity"), "validityStatus"),
        "since": _first(record.find(f"{_SIT}validity"), "overallStartTime"),
        "until": _first(record.find(f"{_SIT}validity"), "overallEndTime"),
        "from": start,
        "to": end,
        "comments": _comments(record),
    }


def parse(body: bytes) -> dict:
    """The feed as {"published_at", "records"}. Pure. Raises ValueError on anything but DATEX II."""
    try:
        root = ET.fromstring(body)
    except ET.ParseError as error:
        raise ValueError(f"DGT feed is not XML: {error}") from error
    if _local(root) != "payload":
        raise ValueError(f"DGT feed has an unexpected root <{_local(root)}>")
    records = []
    for situation in root.iter(f"{_SIT}situation"):
        for record in situation.iter(f"{_SIT}situationRecord"):
            if (parsed := parse_record(record, situation.get("id"))) is not None:
                records.append(parsed)
    published = next((child.text for child in root if _local(child) == "publicationTime"), None)
    return {"published_at": published, "records": records}
