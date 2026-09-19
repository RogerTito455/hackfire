import pytest
from fastapi.testclient import TestClient

from app import crew_plan
from app.main import app

client = TestClient(app)

# Minutes from the fire station to each resident, instead of the cached routes.
DRIVE = {"n01": 20, "n02": 10, "n03": 30, "n04": 15, "n05": 25}


@pytest.fixture(autouse=True)
def fresh(monkeypatch: pytest.MonkeyPatch):
    client.post("/api/reset")
    monkeypatch.setattr(crew_plan, "drive_minutes", lambda neighbor: DRIVE[neighbor.id])


def rescue(*neighbor_ids: str) -> None:
    for neighbor_id in neighbor_ids:
        client.post("/tools/report_status", json={"neighbor_id": neighbor_id, "status": "needs_rescue"})


def test_the_plan_follows_the_rescue_queue_and_splits_it_between_crews() -> None:
    rescue("n01", "n02", "n04")
    queue = [r["neighbor"]["id"] for r in client.get("/api/rescues").json()]

    plan = client.get("/api/crew-plan", params={"crews": 2}).json()

    steps = plan["assignments"]
    assert [s["neighbor_id"] for s in steps] == queue
    # The two most urgent leave at once, one crew each; the third waits for the first crew back.
    assert [s["crew"] for s in steps[:2]] == [1, 2]
    assert [s["depart_min"] for s in steps[:2]] == [0, 0]
    first, third = steps[0], steps[2]
    back = DRIVE[first["neighbor_id"]] * 2 + plan["on_scene_min"]
    second_back = DRIVE[steps[1]["neighbor_id"]] * 2 + plan["on_scene_min"]
    assert third["depart_min"] == min(back, second_back)
    assert third["eta_min"] == third["depart_min"] + DRIVE[third["neighbor_id"]]


def test_a_rescue_the_crew_reaches_after_the_fire_is_flagged_late(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(crew_plan, "drive_minutes", lambda neighbor: 10_000)
    rescue("n01")

    step = client.get("/api/crew-plan", params={"crews": 1}).json()["assignments"][0]

    impact = client.get("/api/rescues").json()[0]["minutes_to_impact"]
    assert step["margin_min"] == impact - 10_000
    assert step["verdict"] == "late"


def test_with_time_to_spare_the_verdict_is_in_time() -> None:
    rescue("n01")

    step = client.get("/api/crew-plan", params={"crews": 1}).json()["assignments"][0]

    assert step["eta_min"] == DRIVE["n01"]
    assert step["verdict"] == "in_time"
