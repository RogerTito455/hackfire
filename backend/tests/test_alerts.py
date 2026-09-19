from fastapi.testclient import TestClient

from app.config import settings
from app.main import app

client = TestClient(app)


def setup_function() -> None:
    client.post("/api/reset")


def report(neighbor_id: str, status: str, **fields) -> None:
    response = client.post("/tools/report_status", json={"neighbor_id": neighbor_id, "status": status, **fields})
    assert response.status_code == 200


def test_a_new_rescue_alerts_the_crew_with_address_people_mobility_and_link() -> None:
    neighbor = client.get("/api/neighbors").json()[0]
    report(neighbor["id"], "needs_rescue", people=2, mobility="mother cannot walk")

    alerts = client.get("/api/alerts").json()
    assert len(alerts) == 1
    alert = alerts[0]
    assert alert["link"] == f"{settings.public_url}/?rescue={neighbor['id']}"
    assert alert["message"] == (
        f"Rescue needed at {neighbor['address']}. 2 people, mother cannot walk. Route: {alert['link']}"
    )
    assert alert["sent_by_sms"] is False


def test_one_alert_per_rescue_not_per_report() -> None:
    neighbor_id = client.get("/api/neighbors").json()[0]["id"]
    report(neighbor_id, "needs_rescue")
    report(neighbor_id, "needs_rescue", observation="smoke closer")
    assert len(client.get("/api/alerts").json()) == 1
    assert "Number of people unknown" in client.get("/api/alerts").json()[0]["message"]


def test_evacuating_residents_do_not_alert_the_crew() -> None:
    neighbor_id = client.get("/api/neighbors").json()[0]["id"]
    report(neighbor_id, "evacuating", people=3)
    assert client.get("/api/alerts").json() == []


def test_alerts_are_newest_first_and_cleared_by_reset() -> None:
    first, second = [n["id"] for n in client.get("/api/neighbors").json()[:2]]
    report(first, "needs_rescue")
    report(second, "needs_rescue")
    assert [a["neighbor_id"] for a in client.get("/api/alerts").json()] == [second, first]
    client.post("/api/reset")
    assert client.get("/api/alerts").json() == []
