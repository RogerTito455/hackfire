from dataclasses import replace

import pytest
from fastapi.testclient import TestClient

from app import scenario
from app.config import DATA_DIR, REPO_ROOT
from app.main import app
from app.pipelines import fetch_hotspots, fetch_zones

client = TestClient(app)


def test_the_demo_is_the_default_scenario() -> None:
    demo = scenario.current()
    assert demo.id == "el-tiemblo-2026-07-23"
    assert demo.files.hotspots == DATA_DIR / "hotspots_2026-07-22_24.geojson"
    assert demo.files.lead_time == DATA_DIR / "lead_time_la-atalaya.json"
    assert demo.files.local_registry == DATA_DIR / "neighbors.local.json"


def test_the_dashboard_gets_the_demo_box_and_window() -> None:
    info = client.get("/api/scenario").json()
    assert info["bbox"] == [-4.85, 40.3, -4.4, 40.5]
    assert (info["replay_start"], info["replay_end"]) == ("2026-07-22T00:00:00Z", "2026-07-25T00:00:00Z")
    assert info["scenario_time"] == "2026-07-23T16:00:00Z"
    assert info["lead_time_zone"] == "la-atalaya"


def test_the_downloads_ask_for_the_same_box_as_before() -> None:
    # The constants the pipelines had before scenarios, as numbers: "40.30" and "40.3" are one box.
    demo = scenario.current()
    as_numbers = lambda text: [float(v) for v in text.split(",")]  # noqa: E731
    assert as_numbers(fetch_hotspots.bbox_parameter(demo.bbox)) == as_numbers("-4.85,40.30,-4.40,40.50")
    assert as_numbers(fetch_zones.overpass_bbox(demo.bbox)) == as_numbers("40.30,-4.85,40.50,-4.40")
    assert [(p.id, p.lon, p.lat, p.radius_m) for p in demo.places] == [
        ("la-atalaya", -4.46095, 40.3821, 1000),
        ("el-tiemblo", -4.499, 40.413, 1500),
    ]


def test_a_scenario_is_named_by_id_or_by_path() -> None:
    assert scenario.path_of("el-tiemblo-2026-07-23") == DATA_DIR / "scenarios" / "el-tiemblo-2026-07-23.json"
    assert scenario.path_of("backend/tests/fixtures/straight-fire/scenario.json") == (
        REPO_ROOT / "backend/tests/fixtures/straight-fire/scenario.json"
    )


def test_activating_a_scenario_forgets_what_was_read_from_the_last_one() -> None:
    demo = scenario.current()
    read = []

    @scenario.cached
    def zone_count() -> int:
        read.append(scenario.current().id)
        return len(read)

    zone_count()
    zone_count()
    scenario.activate(replace(demo, id="other"))
    try:
        zone_count()
    finally:
        scenario.activate(demo)
    assert read == ["el-tiemblo-2026-07-23", "other"]


def test_a_time_without_a_zone_is_refused(tmp_path) -> None:
    raw = (DATA_DIR / "scenarios" / "el-tiemblo-2026-07-23.json").read_text(encoding="utf-8")
    path = tmp_path / "naive.json"
    path.write_text(raw.replace('"2026-07-23T16:00:00Z"', '"2026-07-23T16:00:00"'), encoding="utf-8")
    with pytest.raises(ValueError, match="time zone"):
        scenario.load(path)
