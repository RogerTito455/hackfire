"""The DGT's official road incidents: DATEX II parsing, the cache and its stale path, the footprint filter.

The fixture is trimmed from the real feed (nap.dgt.es, 2026-09-19 22:26 CEST): three forest-fire
records, a road closed on a stretch, a closed carriageway at a point and a roadworks situation. Road
incidents carry no personal data. No test reaches the network.
"""

from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient
from shapely.geometry import box

from app import live_dgt
from app.main import app
from app.providers import dgt

client = TestClient(app)

FIXTURE = Path(__file__).parent / "fixtures" / "dgt" / "datex2_sample.xml"


def _feed() -> dict:
    return dgt.parse(FIXTURE.read_bytes())


def _dgt_up(monkeypatch: pytest.MonkeyPatch, calls: list[str]) -> None:
    def fetch() -> tuple[list[dict], str | None]:
        calls.append("dgt")
        feed = _feed()
        return live_dgt.relevant(feed["records"]), feed["published_at"]

    monkeypatch.setattr(live_dgt, "_fetch", fetch)


def _dgt_down(monkeypatch: pytest.MonkeyPatch) -> None:
    def down() -> tuple[list[dict], str | None]:
        raise httpx.HTTPStatusError("503", request=httpx.Request("GET", "https://x"), response=httpx.Response(503))

    monkeypatch.setattr(live_dgt, "_fetch", down)


# --- Parsing -------------------------------------------------------------------------------------


def test_parsing_reads_every_record_with_its_road_position_and_start() -> None:
    feed = _feed()
    assert feed["published_at"] == "2026-09-19T22:26:48.419+02:00"
    assert len(feed["records"]) == 9
    n340 = next(record for record in feed["records"] if record["id"] == "28096258")
    assert (n340["road"], n340["cause"], n340["cause_detail"], n340["management"]) == (
        "N-340",
        "environmentalObstruction",
        "forestFire",
        "carriagewayClosures",
    )
    assert n340["forest_fire"] is True and n340["closure"] is True
    assert n340["since"] == "2026-09-19T21:04:56.000+02:00"
    assert (n340["from"]["lat"], n340["from"]["lon"], n340["from"]["km"]) == (36.747345, -3.078454, 382.5)
    assert (n340["from"]["municipality"], n340["from"]["province"]) == ("Adra", "Almería")
    assert n340["to"] is None and n340["validity"] == "active"


def test_a_stretch_has_both_ends() -> None:
    closed = next(record for record in _feed()["records"] if record["management"] == "roadClosed")
    assert closed["road"] == "A-8005" and closed["closure"] is True and closed["forest_fire"] is False
    assert (closed["from"]["lat"], closed["from"]["lon"]) == (37.43413, -5.96623)
    assert (closed["to"]["lat"], closed["to"]["lon"]) == (37.451286, -5.954697)


def test_only_forest_fires_and_road_or_carriageway_closures_are_kept() -> None:
    kept = live_dgt.relevant(_feed()["records"])
    assert sorted(record["road"] for record in kept) == ["A-1", "A-4", "A-8005", "FV-1", "N-340"]
    assert sum(record["forest_fire"] for record in kept) == 3


def test_anything_but_datex_ii_is_refused() -> None:
    with pytest.raises(ValueError):
        dgt.parse(b"<html>maintenance</html>")
    with pytest.raises(ValueError):
        dgt.parse(b"not xml at all")


def test_a_feed_that_declares_entities_is_refused() -> None:
    """XXE and entity-expansion bombs: the feed comes from outside, so it is not trusted to be plain XML."""
    external = b'<?xml version="1.0"?><!DOCTYPE payload [<!ENTITY leak SYSTEM "file:///etc/passwd">]><payload>&leak;</payload>'
    bomb = (
        b'<?xml version="1.0"?><!DOCTYPE payload [<!ENTITY a "aaaaaaaaaa"><!ENTITY b "&a;&a;&a;&a;&a;">]>'
        b"<payload>&b;&b;&b;</payload>"
    )
    for body in (external, bomb):
        with pytest.raises(ValueError, match="not safe XML"):
            dgt.parse(body)


# --- Near a fire ---------------------------------------------------------------------------------


def test_records_within_the_area_forest_fires_first() -> None:
    kept = live_dgt.relevant(_feed()["records"])
    # Around Seville: the A-8005 stretch and the A-4 carriageway closure, no fire.
    near_seville = live_dgt.near(kept, box(-6.0, 37.4, -5.7, 37.5))
    assert [record["road"] for record in near_seville] == ["A-4", "A-8005"]  # newest first
    # A box that holds only the stretch's far end still catches it.
    assert [r["road"] for r in live_dgt.near(kept, box(-5.96, 37.445, -5.95, 37.46))] == ["A-8005"]
    # Around Adra: the N-340 forest fire.
    assert [record["id"] for record in live_dgt.near(kept, box(-3.1, 36.7, -3.0, 36.8))] == ["28096258"]
    assert live_dgt.near(kept, box(0, 0, 1, 1)) == []


# --- The cache -----------------------------------------------------------------------------------


def test_the_feed_is_fetched_once_while_fresh(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []
    _dgt_up(monkeypatch, calls)
    first = live_dgt.snapshot()
    second = live_dgt.snapshot()
    assert calls == ["dgt"] and first == second and first["stale"] is False
    assert first["source"] == "DGT" and live_dgt.CACHE_FILE.exists()


def test_an_outage_serves_the_last_answer_as_stale_even_after_a_restart(monkeypatch: pytest.MonkeyPatch) -> None:
    _dgt_up(monkeypatch, [])
    good = live_dgt.snapshot()

    live_dgt.reset_cache()  # as after a restart: only the file is left
    _dgt_down(monkeypatch)
    stale = live_dgt.snapshot()
    assert stale["stale"] is True and stale["records"] == good["records"]
    assert stale["fetched_at"] == good["fetched_at"]


def test_an_outage_with_nothing_cached_is_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    _dgt_down(monkeypatch)
    with pytest.raises(live_dgt.DgtUnavailable):
        live_dgt.snapshot()
    # For one fire it never fails: it says the DGT is not available.
    body = live_dgt.near_area(box(0, 0, 1, 1))
    assert body["available"] is False and body["records"] == []


# --- The endpoint --------------------------------------------------------------------------------


def test_endpoint_lists_forest_fires_and_closures_apart(monkeypatch: pytest.MonkeyPatch) -> None:
    _dgt_up(monkeypatch, [])
    body = client.get("/api/live/dgt").json()
    assert [record["road"] for record in body["forest_fires"]] == ["FV-1", "A-1", "N-340"]
    assert sorted(record["road"] for record in body["closures"]) == ["A-4", "A-8005"]
    assert body["source"] == "DGT" and body["stale"] is False


def test_endpoint_with_the_dgt_down_and_nothing_cached_is_a_503(monkeypatch: pytest.MonkeyPatch) -> None:
    _dgt_down(monkeypatch)
    assert client.get("/api/live/dgt").status_code == 503
