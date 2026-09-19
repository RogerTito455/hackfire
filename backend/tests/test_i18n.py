"""The backend's sentences in every language: same keys, same placeholders, the right one per caller."""

import json
import re

import pytest
from fastapi.testclient import TestClient

from app import briefing, evacuation, i18n
from app.config import settings
from app.main import app
from app.models import TravelMode
from app.providers import routing
from app.state import state

client = TestClient(app)
PLURAL_FORMS = {"zero", "one", "two", "few", "many", "other"}


def leaves(node: dict, prefix: str = "") -> dict[str, set[str]]:
    """Every sentence key with its placeholders; a plural object counts as one sentence."""
    found: dict[str, set[str]] = {}
    for key, value in node.items():
        path = f"{prefix}.{key}" if prefix else key
        if path == "_meta":
            continue
        if isinstance(value, str):
            found[path] = set(re.findall(r"\{(\w+)\}", value))
        elif set(value) <= PLURAL_FORMS:
            assert "other" in value, f"{path}: a plural needs an 'other' form"
            found[path] = set(re.findall(r"\{(\w+)\}", " ".join(value.values())))
        else:
            found.update(leaves(value, path))
    return found


def test_every_locale_has_the_reference_sentences_and_placeholders() -> None:
    reference = leaves(i18n.catalogue()["en"])
    for code, messages in i18n.catalogue().items():
        assert messages["_meta"]["name"], code
        assert leaves(messages) == reference, code


def test_accept_language_picks_the_best_locale_we_have() -> None:
    assert i18n.negotiate("es-ES,es;q=0.9,en;q=0.8") == "es"
    assert i18n.negotiate("fr-FR,fr;q=0.9,es;q=0.5") == "es"
    assert i18n.negotiate("de, en;q=0.1") == "en"
    assert i18n.negotiate(None) == "en"
    assert i18n.resolve("es_ES") == "es"


def test_plural_forms_and_placeholders() -> None:
    assert i18n.t("crew.people", "en", count=1) == "1 person"
    assert i18n.t("crew.people", "es", count=3) == "3 personas"
    assert i18n.t("order.stay", "es", zone="El Tiemblo").startswith("La orden para El Tiemblo")


def test_every_cached_route_reads_back_into_data_without_losing_a_word() -> None:
    cache = json.loads(evacuation.CACHE_FILE.read_text(encoding="utf-8"))
    assert cache
    with i18n.using("en"):
        for key, cached in cache.items():
            data = evacuation.legacy_directions(cached)
            assert data is not None, key
            # The only change: the old template said "1 minutes" and "1 kilometres".
            original = cached["spoken_directions"].replace(" 1 kilometres", " 1 kilometre").replace(" 1 minutes", " 1 minute")
            assert evacuation.say(data) == original, key


def test_a_cached_route_is_said_in_spanish_to_a_spanish_dashboard() -> None:
    neighbor = client.get("/api/neighbors").json()[0]
    english = client.get(f"/api/routes/{neighbor['id']}").json()["spoken_directions"]
    spanish = client.get(f"/api/routes/{neighbor['id']}", headers={"Accept-Language": "es-ES,es;q=0.9"}).json()
    assert english.startswith("Drive to ")
    assert spanish["spoken_directions"].startswith("Ve en coche hasta ")
    assert client.get(f"/api/routes/{neighbor['id']}?lang=es").json() == spanish


def test_directions_say_the_roads_and_how_far_in_spanish() -> None:
    data = {
        "mode": "walking",
        "destination": "Cebreros",
        "roads": ["N-403", "Carretera de Ávila"],
        "distance_m": 8_400,
        "duration_s": 8_385,
        "avoids": "ahead",
        "ahead_h": 1,
    }
    with i18n.using("es"):
        assert evacuation.say(data) == (
            "Ve a pie hasta Cebreros por N-403, luego por Carretera de Ávila. "
            "Son unos 8 kilómetros, unas 2 horas y 20 minutos a pie. "
            "Esta ruta se aleja del fuego y de por donde se espera que avance en la próxima hora."
        )


def test_a_new_route_keeps_its_data_so_it_can_be_said_in_another_language(monkeypatch: pytest.MonkeyPatch) -> None:
    feature = {
        "type": "Feature",
        "geometry": {"type": "LineString", "coordinates": [[-4.46, 40.38], [-4.40, 40.36]]},
        "properties": {"summary": {"distance": 600, "duration": 50}, "segments": [{"steps": []}]},
    }
    monkeypatch.setattr(evacuation, "_disk_cache", lambda: {})
    monkeypatch.setattr(evacuation, "_memory", {})
    monkeypatch.setattr(routing, "route_avoiding", lambda *_args: feature)
    args = ((-4.46, 40.38), (-4.40, 40.36), TravelMode.CAR, "Cebreros", settings.scenario_time)
    with i18n.using("es"):
        first = evacuation.plan(*args)
    with i18n.using("en"):
        again = evacuation.plan(*args)
    assert first.spoken_directions.startswith("Ve en coche hasta Cebreros.")
    assert again.spoken_directions.startswith("Drive to Cebreros. It is about 600 metres, around 1 minute by car.")


def test_the_agents_tools_answer_in_the_agent_locale_whatever_the_header() -> None:
    status = client.post("/tools/get_fire_status", json={"zone": "la-atalaya"}, headers={"Accept-Language": "es"})
    assert "La Atalaya" in status.json()["summary"]
    with i18n.using(settings.agent_locale):
        expected = briefing.fire_summary("la-atalaya", state.minutes_to_impact("la-atalaya"))
    assert status.json()["summary"] == expected


def test_call_data_stays_in_the_agent_locale_when_the_dashboard_is_in_spanish() -> None:
    neighbor = state.neighbors()[0]
    with i18n.using("es"):
        variables = briefing.call_variables(neighbor)
    with i18n.using(settings.agent_locale):
        assert variables["fire_status"] == briefing.fire_summary(neighbor.zone, state.minutes_to_impact(neighbor.zone))


def test_crew_alerts_are_read_in_the_dashboard_language() -> None:
    client.post("/api/reset")
    neighbor = client.get("/api/neighbors").json()[0]
    client.post("/tools/report_status", json={"neighbor_id": neighbor["id"], "status": "needs_rescue", "people": 2})
    spanish = client.get("/api/alerts", headers={"Accept-Language": "es"}).json()[0]["message"]
    assert spanish.startswith(f"Rescate necesario en {neighbor['address']}. 2 personas.")
    client.post("/api/reset")
