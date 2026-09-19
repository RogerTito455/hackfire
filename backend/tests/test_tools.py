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
    neighbors = client.get("/api/neighbors").json()
    far = next(n for n in neighbors if n["zone"] == "el-tiemblo")
    near = next(n for n in neighbors if n["zone"] == "la-atalaya")

    for neighbor in (far, near):
        client.post("/tools/report_status", json={"neighbor_id": neighbor["id"], "status": "needs_rescue"})

    queue = client.post("/tools/get_rescue_queue").json()
    assert [r["neighbor"]["id"] for r in queue] == [near["id"], far["id"]]


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


def test_unknown_neighbor_is_404() -> None:
    response = client.post("/tools/report_status", json={"neighbor_id": "nope", "status": "evacuating"})
    assert response.status_code == 404
