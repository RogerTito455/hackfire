"""Live operations for one real fire: places at risk, time to impact, alert drafts and roads to close.

Everything here runs on fakes: no Deepfire, no Overpass.
"""

import re
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient
from shapely.geometry import box, mapping, shape

from app import cap, i18n, impact, live, live_dgt, live_operations, live_spread
from app.main import app
from app.providers import overpass

client = TestClient(app)

RUN_AT = datetime(2026, 9, 19, 12, 0, tzinfo=UTC)
NOW = datetime(2026, 9, 19, 12, 30, tzinfo=UTC)  # the run is half an hour old

# A fire running east along latitude 40: hour h reaches lon 0.01 * h.
HOURS = [{"hour": hour, "geometry": mapping(box(0, 40, 0.01 * hour, 40.01))} for hour in (3, 2, 1)]


def _node(osm_id: int, lon: float, lat: float, **tags: str) -> dict:
    return {"type": "node", "id": osm_id, "lon": lon, "lat": lat, "tags": tags}


def _way(osm_id: int, coords: list[tuple[float, float]], **tags: str) -> dict:
    return {"type": "way", "id": osm_id, "geometry": [{"lon": lon, "lat": lat} for lon, lat in coords], "tags": tags}


ELEMENTS = [
    _node(1, 0.005, 40.005, place="village", name="Villa Uno"),  # hour 1
    _node(2, 0.015, 40.005, amenity="school", name="Escuela Dos"),  # hour 2
    _way(3, [(0.025, 39.99), (0.025, 40.02)], highway="secondary", ref="CV-1"),  # hour 3
    _node(4, 0.035, 40.005, amenity="nursing_home"),  # ~400 m past hour 3: near, not reached
    _node(5, 0.2, 40.2, place="town", name="Lejos"),  # far outside the buffer
    _way(6, [(0.004, 40.004), (0.006, 40.004), (0.006, 40.006), (0.004, 40.004)], landuse="residential", name="Villa Uno"),
]


def _run(fire_id: str = "c1", simulation_id: str = "sim-1") -> dict:
    return {
        "fire_id": fire_id,
        "simulation_id": simulation_id,
        "name": "Somewhere, Somewhere",
        "location": "Somewhere",
        "created_at": "2026-09-19T12:00:00Z",
        "model": "elmfire",
        "duration_hours": 12,
        "ensemble_members": 1,
        "burned_area_m2": 1.0,
        "hours": HOURS,
    }


@pytest.fixture(autouse=True)
def fresh_cache(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    monkeypatch.setattr(live_operations, "CACHE_DIR", tmp_path / "live_places")
    live_operations.reset_cache()
    yield
    live_operations.reset_cache()


def _overpass_up(monkeypatch: pytest.MonkeyPatch, calls: list[str]) -> None:
    monkeypatch.setattr(live_operations, "_fetch_elements", lambda area: calls.append("overpass") or ELEMENTS)


def _overpass_down(monkeypatch: pytest.MonkeyPatch) -> None:
    def busy(_area: object) -> list[dict]:
        raise httpx.HTTPStatusError("504", request=httpx.Request("POST", "https://x"), response=httpx.Response(504))

    monkeypatch.setattr(live_operations, "_fetch_elements", busy)


def _deepfire(monkeypatch: pytest.MonkeyPatch, *runs: dict, stale: bool = False) -> None:
    body = {"fires": list(runs), "fetched_at": "2026-09-19T12:29:00+00:00", "stale": stale}
    monkeypatch.setattr(live_spread, "predicted_spread", lambda: body)


def _places(now: datetime = NOW) -> list[dict]:
    hourly = live_operations.hourly_polygons(HOURS)
    area = live_operations.search_area(hourly)
    return live_operations.assess(live_operations.parse_places(ELEMENTS, area), hourly, RUN_AT, now)


# --- Time to impact ------------------------------------------------------------------------------


def test_first_hour_touching_is_the_first_cumulative_polygon_that_reaches_the_place() -> None:
    hourly = live_operations.hourly_polygons(HOURS)
    assert impact.first_hour_touching(hourly, box(0.001, 40.001, 0.002, 40.002)) == 1
    assert impact.first_hour_touching(hourly, box(0.019, 40.001, 0.021, 40.002)) == 2
    assert impact.first_hour_touching(hourly, box(0.05, 40.001, 0.06, 40.002)) is None


def test_time_to_impact_counts_from_the_run_and_what_is_left_of_it_now() -> None:
    places = {place["name"]: place for place in _places()}

    assert (places["Villa Uno"]["hour"], places["Villa Uno"]["minutes_from_run"], places["Villa Uno"]["minutes"]) == (1, 60, 30)
    assert (places["Escuela Dos"]["minutes_from_run"], places["Escuela Dos"]["minutes"]) == (120, 90)
    assert (places["CV-1"]["minutes_from_run"], places["CV-1"]["minutes"]) == (180, 150)
    assert places["Villa Uno"]["reaches_at"] == "2026-09-19T13:00:00Z"


def test_a_place_the_run_already_passed_is_due_now() -> None:
    [first, *_] = _places(now=datetime(2026, 9, 19, 16, 0, tzinfo=UTC))
    assert first["name"] == "Villa Uno" and first["minutes"] == 0


def test_places_come_soonest_first_and_the_ones_never_reached_last() -> None:
    places = _places()
    assert [(p["kind"], p["name"]) for p in places] == [
        ("town", "Villa Uno"),
        ("school", "Escuela Dos"),
        ("road", "CV-1"),
        ("care_home", None),  # within the buffer, never reached
    ]
    assert places[-1]["minutes"] is None and places[-1]["reaches_at"] is None


def test_parsing_pads_place_nodes_merges_estates_and_clips_roads() -> None:
    hourly = live_operations.hourly_polygons(HOURS)
    area = live_operations.search_area(hourly)
    features = {f["id"]: f for f in live_operations.parse_places(ELEMENTS, area)}

    assert set(features) == {"town-n1", "school-n2", "road-cv-1", "care-home-n4"}  # no "Lejos", no duplicate estate
    assert features["town-n1"]["geometry"]["type"] == "Polygon"
    assert features["care-home-n4"]["properties"]["osm"] == "node/4"
    _, south, _, north = shape(features["road-cv-1"]["geometry"]).bounds
    assert south > 39.99 and north < 40.02  # clipped to the footprint plus the buffer


# --- Roads to close and alert drafts -------------------------------------------------------------


def test_roads_the_run_reaches_within_the_hour_are_closed_to_residents() -> None:
    places = [
        {"id": "road-a", "kind": "road", "minutes": 0},
        {"id": "road-b", "kind": "road", "minutes": 60},
        {"id": "road-c", "kind": "road", "minutes": 61},
        {"id": "road-d", "kind": "road", "minutes": None},
        {"id": "town-x", "kind": "town", "minutes": 10},
    ]
    assert live_operations.roads_to_close(places) == ["road-a", "road-b"]


def test_alert_drafts_in_spanish() -> None:
    drafts = live_operations.alert_drafts(_places(now=datetime(2026, 9, 19, 12, 45, tzinfo=UTC)), "es")

    assert [draft["zone_id"] for draft in drafts] == ["town-n1", "school-n2"]  # no roads, nothing unreached
    assert drafts[0]["text"] == (
        "Incendio forestal cerca de Villa Uno: la simulación prevé que llegue en menos de una hora. "
        "Siga las indicaciones de Protección Civil y del 112."
    )
    assert drafts[1]["text"] == (
        "Incendio forestal cerca de Escuela Dos: la simulación prevé que llegue en aproximadamente una hora. "
        "Siga las indicaciones de Protección Civil y del 112."
    )
    assert all(draft["draft"] is True and draft["sent"] is False for draft in drafts)


def test_alert_drafts_in_english_with_hours_due_and_unnamed_places() -> None:
    places = [
        {"id": "a", "name": "Aldea", "kind": "town", "minutes": 0},
        {"id": "b", "name": "Barrio", "kind": "estate", "minutes": 185},
        {"id": "c", "name": None, "kind": "care_home", "minutes": 300},
    ]
    texts = [draft["text"] for draft in live_operations.alert_drafts(places, "en")]
    assert texts == [
        "Wildfire near Aldea: according to the simulation, it may already be arriving. Follow the instructions of Civil Protection and 112.",
        "Wildfire near Barrio: the simulation expects it to arrive in about 3 hours. Follow the instructions of Civil Protection and 112.",
        "Wildfire near an unnamed care home: the simulation expects it to arrive in about 5 hours. Follow the instructions of Civil Protection and 112.",
    ]


# --- The places cache ----------------------------------------------------------------------------


def test_places_are_fetched_once_per_simulation_and_survive_a_restart(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []
    _overpass_up(monkeypatch, calls)
    hourly = live_operations.hourly_polygons(HOURS)

    first, stale = live_operations.places_for("sim-1", "c1", hourly)
    second, _ = live_operations.places_for("sim-1", "c1", hourly)
    assert calls == ["overpass"] and second == first and stale is False
    assert (live_operations.CACHE_DIR / "sim-1.json").exists()

    live_operations.reset_cache()  # as after a restart
    _overpass_down(monkeypatch)
    after, stale = live_operations.places_for("sim-1", "c1", hourly)
    assert after == first and stale is False


def test_overpass_down_serves_an_earlier_run_of_the_same_fire_as_stale(monkeypatch: pytest.MonkeyPatch) -> None:
    _overpass_up(monkeypatch, [])
    hourly = live_operations.hourly_polygons(HOURS)
    earlier, _ = live_operations.places_for("sim-1", "c1", hourly)

    _overpass_down(monkeypatch)
    entry, stale = live_operations.places_for("sim-2", "c1", hourly)  # a newer run of the same fire
    assert stale is True and entry["features"] == earlier["features"]

    with pytest.raises(live_operations.PlacesUnavailable):
        live_operations.places_for("sim-9", "another-fire", hourly)


# --- The endpoint --------------------------------------------------------------------------------


def test_endpoint_answers_places_drafts_and_roads(monkeypatch: pytest.MonkeyPatch) -> None:
    _deepfire(monkeypatch, _run())
    _overpass_up(monkeypatch, [])

    response = client.get("/api/live/operations/c1", headers={"Accept-Language": "es-ES"})

    assert response.status_code == 200
    body = response.json()
    assert (body["fire_id"], body["simulation_id"], body["model"], body["run_at"]) == ("c1", "sim-1", "elmfire", "2026-09-19T12:00:00Z")
    assert [place["id"] for place in body["places"]][:3] == ["town-n1", "school-n2", "road-cv-1"]
    assert body["alerts"][0]["text"].startswith("Incendio forestal cerca de Villa Uno")
    assert all(alert["sent"] is False for alert in body["alerts"])
    assert body["places_stale"] is False and body["spread_stale"] is False
    assert body["road_closed_within_minutes"] == 60
    # The run is hours old by now, so its whole footprint is due: the road is closed to residents.
    assert body["roads_to_close"] == ["road-cv-1"]


def test_endpoint_for_a_fire_without_a_run_is_a_404(monkeypatch: pytest.MonkeyPatch) -> None:
    _deepfire(monkeypatch, _run())
    assert client.get("/api/live/operations/unknown").status_code == 404


def test_endpoint_with_deepfire_down_is_a_503(monkeypatch: pytest.MonkeyPatch) -> None:
    def down() -> dict:
        raise live.LiveUnavailable("503")

    monkeypatch.setattr(live_spread, "predicted_spread", down)
    assert client.get("/api/live/operations/c1").status_code == 503


def test_endpoint_with_overpass_down_and_nothing_cached_is_a_503(monkeypatch: pytest.MonkeyPatch) -> None:
    _deepfire(monkeypatch, _run())
    _overpass_down(monkeypatch)
    response = client.get("/api/live/operations/c1")
    assert response.status_code == 503
    assert "OpenStreetMap" in response.json()["detail"]


def test_endpoint_marks_stale_places_and_a_stale_spread(monkeypatch: pytest.MonkeyPatch) -> None:
    _deepfire(monkeypatch, _run())
    _overpass_up(monkeypatch, [])
    client.get("/api/live/operations/c1")

    _deepfire(monkeypatch, _run(simulation_id="sim-2"), stale=True)
    _overpass_down(monkeypatch)
    body = client.get("/api/live/operations/c1").json()
    assert body["simulation_id"] == "sim-2"
    assert body["places_stale"] is True and body["spread_stale"] is True


# --- The Overpass provider -----------------------------------------------------------------------


def test_overpass_passes_a_busy_server_on_to_the_next_mirror(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(overpass, "servers", lambda: ["https://busy.example/api", "https://mirror.example/api"])
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.url.host)
        if request.url.host == "busy.example":
            return httpx.Response(504)
        return httpx.Response(200, json={"elements": [{"type": "node", "id": 1}]})

    with httpx.Client(transport=httpx.MockTransport(handler)) as fake:
        assert overpass.elements(fake, "[out:json];node(1);out;") == [{"type": "node", "id": 1}]
    assert seen == ["busy.example", "mirror.example"]


def test_overpass_raises_when_every_server_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(overpass, "servers", lambda: ["https://a.example/api", "https://b.example/api"])
    with httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(429))) as fake:
        with pytest.raises(httpx.HTTPStatusError):
            overpass.elements(fake, "[out:json];node(1);out;")


def test_backend_locales_have_the_live_drafts() -> None:
    for code in ("en", "es"):
        assert "{place}" in i18n.t("liveOps.alertDue", code)


# --- Official DGT records near the fire ----------------------------------------------------------


def _dgt_record(record_id: str, lon: float, lat: float, **fields: object) -> dict:
    point = {"lat": lat, "lon": lon, "km": 1.0, "municipality": "M", "province": "P", "community": "C"}
    return {
        "id": record_id, "situation_id": "s" + record_id, "record_type": "RoadOrCarriagewayOrLaneManagement",
        "road": "CV-1", "destination": None, "direction": None, "cause": "roadMaintenance", "cause_detail": "roadworks",
        "management": "roadClosed", "forest_fire": False, "closure": True, "severity": None, "validity": "active",
        "since": "2026-09-19T10:00:00.000+02:00", "until": None, "from": point, "to": None, "comments": [],
        **fields,
    }  # fmt: skip


def test_endpoint_lists_the_official_dgt_records_near_the_footprint(monkeypatch: pytest.MonkeyPatch) -> None:
    _deepfire(monkeypatch, _run())
    _overpass_up(monkeypatch, [])
    records = [
        _dgt_record("1", 0.025, 40.005),  # on the footprint
        _dgt_record("2", 0.07, 40.005, forest_fire=True, cause="environmentalObstruction", cause_detail="forestFire"),  # ~4 km away
        _dgt_record("3", 0.2, 40.2),  # far
    ]
    monkeypatch.setattr(live_dgt, "_fetch", lambda: (records, "2026-09-19T12:00:00+02:00"))

    dgt = client.get("/api/live/operations/c1").json()["dgt"]

    assert dgt["available"] is True and dgt["source"] == "DGT" and dgt["near_m"] == live_dgt.NEAR_FIRE_M
    assert [record["id"] for record in dgt["records"]] == ["2", "1"]  # forest fires first


def test_endpoint_still_answers_when_the_dgt_is_down(monkeypatch: pytest.MonkeyPatch) -> None:
    _deepfire(monkeypatch, _run())
    _overpass_up(monkeypatch, [])
    body = client.get("/api/live/operations/c1").json()  # conftest keeps the DGT offline
    assert body["dgt"]["available"] is False and body["places"]


# --- CAP 1.2 drafts ------------------------------------------------------------------------------

CAP = "{urn:oasis:names:tc:emergency:cap:1.2}"
# The element order of the CAP 1.2 schema (http://docs.oasis-open.org/emergency/cap/v1.2/CAP-v1.2.xsd).
ALERT_ORDER = ["identifier", "sender", "sent", "status", "msgType", "source", "scope", "restriction", "addresses", "code", "note", "references", "incidents", "info"]
INFO_ORDER = ["language", "category", "event", "responseType", "urgency", "severity", "certainty", "audience", "eventCode", "effective", "onset", "expires", "senderName", "headline", "description", "instruction", "web", "contact", "parameter", "resource", "area"]
AREA_ORDER = ["areaDesc", "polygon", "circle", "geocode", "altitude", "ceiling"]
CAP_TIME = r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d[-+]\d\d:\d\d$"


def _in_schema_order(element: ET.Element, order: list[str]) -> bool:
    names = [child.tag.removeprefix(CAP) for child in element]
    return all(name in order for name in names) and names == sorted(names, key=order.index)


def _cap(monkeypatch: pytest.MonkeyPatch) -> tuple[httpx.Response, ET.Element]:
    _deepfire(monkeypatch, _run())
    _overpass_up(monkeypatch, [])
    response = client.get("/api/live/operations/c1/cap")
    assert response.status_code == 200
    return response, ET.fromstring(response.content)  # well-formed, or this raises


def test_cap_is_a_draft_never_an_actual_alert(monkeypatch: pytest.MonkeyPatch) -> None:
    response, alert = _cap(monkeypatch)

    assert response.headers["content-type"].startswith("application/cap+xml")
    assert "attachment" in response.headers["content-disposition"]
    assert alert.tag == f"{CAP}alert" and _in_schema_order(alert, ALERT_ORDER)
    assert alert.findtext(f"{CAP}status") == "Draft"
    assert (alert.findtext(f"{CAP}msgType"), alert.findtext(f"{CAP}scope"), alert.findtext(f"{CAP}sender")) == ("Alert", "Public", "hackfire")
    assert re.match(CAP_TIME, alert.findtext(f"{CAP}sent"))
    assert re.match(r"^[A-Za-z0-9._-]+$", alert.findtext(f"{CAP}identifier"))
    assert "Actual" not in response.text


def test_cap_has_one_info_per_language_with_an_area_per_drafted_place(monkeypatch: pytest.MonkeyPatch) -> None:
    _, alert = _cap(monkeypatch)
    infos = alert.findall(f"{CAP}info")

    assert [info.findtext(f"{CAP}language") for info in infos] == ["es-ES", "en-GB"]  # the residents' language first
    for info in infos:
        assert _in_schema_order(info, INFO_ORDER)
        assert (info.findtext(f"{CAP}category"), info.findtext(f"{CAP}severity"), info.findtext(f"{CAP}certainty")) == ("Fire", "Severe", "Likely")
        # The run is hours old, so the first place is due: Immediate.
        assert info.findtext(f"{CAP}urgency") == "Immediate"
        assert re.match(CAP_TIME, info.findtext(f"{CAP}expires"))
        areas = info.findall(f"{CAP}area")
        assert [area.findtext(f"{CAP}areaDesc") for area in areas] == ["Villa Uno", "Escuela Dos"]  # no road, nothing unreached
        for area in areas:
            assert _in_schema_order(area, AREA_ORDER)
            assert area.findall(f"{CAP}polygon") or area.findall(f"{CAP}circle")
            for polygon in area.findall(f"{CAP}polygon"):
                pairs = polygon.text.split()
                assert len(pairs) >= 4 and pairs[0] == pairs[-1]
                lat, lon = map(float, pairs[0].split(","))
                assert 39.9 < lat < 40.1 and -0.1 < lon < 0.1  # lat,lon order
            for circle in area.findall(f"{CAP}circle"):
                assert re.match(r"^-?\d+\.\d+,-?\d+\.\d+ \d+(\.\d+)?$", circle.text)
    spanish, english = infos
    assert spanish.findtext(f"{CAP}headline") == "Incendio forestal cerca de Villa Uno y de otro lugar"
    description = english.findtext(f"{CAP}description")
    assert "Villa Uno" in description and "not an official warning" in description


def test_cap_urgency_is_expected_when_no_place_is_reached_within_the_hour() -> None:
    operations = {
        "fire_id": "c1", "simulation_id": "sim-1", "run_at": "2026-09-19T12:00:00Z", "model": "elmfire", "duration_hours": 12,
        "places": [{"id": "town-x", "name": "Aldea", "kind": "town", "minutes": 185, "geometry": {"type": "Point", "coordinates": [0.1, 40.1]}}],
    }  # fmt: skip
    alert = ET.fromstring(cap.document(operations, now=NOW))
    info = alert.find(f"{CAP}info")
    assert info.findtext(f"{CAP}urgency") == "Expected"
    assert info.find(f"{CAP}area").findtext(f"{CAP}circle") == "40.10000,0.10000 0.2"
    assert alert.findtext(f"{CAP}sent") == "2026-09-19T12:30:00-00:00"
    assert alert.findtext(f"{CAP}status") == "Draft"


def test_cap_without_drafts_is_a_404(monkeypatch: pytest.MonkeyPatch) -> None:
    far = {**_run(), "hours": [{"hour": 1, "geometry": mapping(box(5, 45, 5.001, 45.001))}]}
    _deepfire(monkeypatch, far)
    _overpass_up(monkeypatch, [])
    assert client.get("/api/live/operations/c1/cap").status_code == 404
