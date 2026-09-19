import json
from collections.abc import Callable, Iterator
from dataclasses import replace

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.main import app
from app.state import state

client = TestClient(app)

PHONE = "+34000111222"


def resident(neighbor_id: str, **overrides) -> dict:
    return {
        "id": neighbor_id,
        "name": f"Resident {neighbor_id}",
        "phone": PHONE,
        "address": f"Calle del Guadiana {neighbor_id}, La Atalaya",
        "zone": "la-atalaya",
        "lat": 40.3827,
        "lon": -4.4564,
    } | overrides


@pytest.fixture
def registry_variable() -> Iterator[Callable[[str], object]]:
    """Set HACKFIRE_NEIGHBORS_JSON as the deployed backend would, and reload the registry."""
    with pytest.MonkeyPatch.context() as patch:

        def use(text: str):
            patch.setattr("app.state.settings", replace(settings, neighbors_json=text))
            return client.post("/api/reset")

        yield use
    # Only this fixture's patch is undone here: conftest's still pins the sample registry.
    state.load()


def test_the_registry_in_the_variable_replaces_the_files(registry_variable) -> None:
    registry_variable(json.dumps([resident("x1"), resident("x2", zone="el-tiemblo")]))

    neighbors = client.get("/api/neighbors").json()

    assert [n["id"] for n in neighbors] == ["x1", "x2"]
    assert neighbors[1]["zone"] == "el-tiemblo"


def test_phone_numbers_from_the_variable_never_reach_the_api(registry_variable) -> None:
    registry_variable(json.dumps([resident("x1")]))
    client.post("/tools/report_status", json={"neighbor_id": "x1", "status": "needs_rescue", "people": 2})

    for path in ("/api/neighbors", "/api/rescues", "/api/alerts"):
        assert PHONE not in client.get(path).text, path


def test_an_empty_variable_falls_back_to_the_registry_files(registry_variable) -> None:
    registry_variable("")

    assert len(client.get("/api/neighbors").json()) >= 1


def test_broken_json_fails_loudly_naming_the_variable_and_hiding_the_numbers(registry_variable) -> None:
    truncated = json.dumps([resident("x1")])[:-15]

    with pytest.raises(ValueError) as error:
        registry_variable(truncated)

    assert "HACKFIRE_NEIGHBORS_JSON" in str(error.value)
    assert PHONE not in str(error.value)


def test_a_resident_missing_a_field_is_reported_by_field_without_the_numbers(registry_variable) -> None:
    incomplete = resident("x1")
    del incomplete["zone"]

    with pytest.raises(ValueError) as error:
        registry_variable(json.dumps([incomplete]))

    message = str(error.value)
    assert "HACKFIRE_NEIGHBORS_JSON" in message
    assert "zone" in message
    assert PHONE not in message


def test_a_registry_with_no_residents_is_refused_instead_of_starting_empty(registry_variable) -> None:
    with pytest.raises(ValueError, match="HACKFIRE_NEIGHBORS_JSON"):
        registry_variable("[]")


def test_a_repeated_id_is_refused_instead_of_silently_dropping_a_resident(registry_variable) -> None:
    with pytest.raises(ValueError) as error:
        registry_variable(json.dumps([resident("x1"), resident("x2"), resident("x1")]))

    assert "resident 3" in str(error.value)
    assert PHONE not in str(error.value)


def test_the_error_says_which_resident_is_wrong(registry_variable) -> None:
    second = resident("x2")
    del second["zone"]

    with pytest.raises(ValueError) as error:
        registry_variable(json.dumps([resident("x1"), second]))

    assert "resident 2" in str(error.value)


def test_a_resident_without_an_id_is_named_as_such(registry_variable) -> None:
    anonymous = resident("x1")
    del anonymous["id"]

    with pytest.raises(ValueError, match="id"):
        registry_variable(json.dumps([anonymous]))


def test_a_bad_resident_in_a_registry_file_does_not_leak_the_phone(tmp_path, monkeypatch) -> None:
    # Short on purpose: pydantic truncates long inputs in its error text, and this one must show the phone.
    incomplete = {"id": "x1", "phone": PHONE}
    broken = tmp_path / "neighbors.json"
    broken.write_text(json.dumps([incomplete]), encoding="utf-8")
    monkeypatch.setattr("app.state._registry_candidates", lambda: [broken])

    with pytest.raises(ValueError) as error:
        client.post("/api/reset")

    assert "zone" in str(error.value)
    assert PHONE not in str(error.value)
