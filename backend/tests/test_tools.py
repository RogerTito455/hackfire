from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def setup_function() -> None:
    client.post("/api/reset")


def test_health() -> None:
    assert client.get("/health").json() == {"status": "ok"}


def test_registry_loads() -> None:
    neighbors = client.get("/api/neighbors").json()
    assert len(neighbors) >= 1
    assert all(n["status"] == "pending" for n in neighbors)


def test_report_status_feeds_rescue_queue() -> None:
    neighbor_id = client.get("/api/neighbors").json()[0]["id"]

    response = client.post(
        "/tools/report_status",
        json={
            "neighbor_id": neighbor_id,
            "status": "needs_rescue",
            "people": 2,
            "mobility": "cannot walk",
            "observation": "smoke coming from the north",
        },
    )
    assert response.status_code == 200
    assert response.json()["status"] == "needs_rescue"

    queue = client.post("/tools/get_rescue_queue").json()
    assert [r["neighbor"]["id"] for r in queue] == [neighbor_id]
    assert queue[0]["priority"] == 1


def test_rescue_queue_orders_by_time_to_impact() -> None:
    # At the default scenario moment both zones are already covered (0 minutes), so pick a moment
    # where the two are apart: 15:00 UTC, when El Tiemblo is 2 hours out and La Atalaya 4.
    client.post("/api/replay/time", json={"at": "2026-07-23T15:00:00Z"})
    neighbors = client.get("/api/neighbors").json()
    minutes = {
        zone: client.post("/tools/get_fire_status", json={"zone": zone}).json()["minutes_to_impact"]
        for zone in ("la-atalaya", "el-tiemblo")
    }
    near_zone, far_zone = sorted(minutes, key=minutes.__getitem__)
    assert minutes[near_zone] < minutes[far_zone]  # otherwise the ordering below proves nothing
    near = next(n for n in neighbors if n["zone"] == near_zone)
    far = next(n for n in neighbors if n["zone"] == far_zone)

    for neighbor in (far, near):
        client.post("/tools/report_status", json={"neighbor_id": neighbor["id"], "status": "needs_rescue"})

    queue = client.post("/tools/get_rescue_queue").json()
    assert [r["neighbor"]["id"] for r in queue] == [near["id"], far["id"]]
    assert queue[0]["minutes_to_impact"] == minutes[near_zone]


def test_reset_restores_the_initial_registry() -> None:
    initial = client.get("/api/neighbors").json()
    report = client.post(
        "/tools/report_status",
        json={"neighbor_id": initial[0]["id"], "status": "needs_rescue", "people": 3, "observation": "smoke"},
    )
    assert report.json()["status"] == "needs_rescue"

    assert client.post("/api/reset").status_code == 200

    assert client.get("/api/neighbors").json() == initial
    assert client.get("/api/rescues").json() == []


# SLNG's API Request tool posts the model's arguments as a raw JSON body and does not check their
# types: nulls, empty strings and numbers as text reach us exactly as the model wrote them.


def test_report_status_accepts_the_nulls_and_empty_strings_an_agent_sends() -> None:
    neighbor_id = client.get("/api/neighbors").json()[0]["id"]

    response = client.post(
        "/tools/report_status",
        json={"neighbor_id": neighbor_id, "status": "needs_rescue", "people": None, "mobility": "", "observation": None},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "needs_rescue"


def test_report_status_reads_people_sent_as_text() -> None:
    neighbor_id = client.get("/api/neighbors").json()[0]["id"]

    response = client.post("/tools/report_status", json={"neighbor_id": neighbor_id, "status": "evacuating", "people": "3"})

    assert response.json()["people"] == 3


def test_report_status_keeps_the_triage_when_people_is_not_a_number() -> None:
    # A rejected call would leave the pin unchanged in the middle of an emergency call.
    neighbor_id = client.get("/api/neighbors").json()[0]["id"]

    response = client.post(
        "/tools/report_status", json={"neighbor_id": neighbor_id, "status": "needs_rescue", "people": "unos tres"}
    )

    assert response.status_code == 200
    assert response.json()["status"] == "needs_rescue"
    assert response.json()["people"] is None


def test_unknown_neighbor_is_404() -> None:
    response = client.post("/tools/report_status", json={"neighbor_id": "nope", "status": "evacuating"})
    assert response.status_code == 404
