"""The audit log: append-only, read back after a restart, newest first, never a phone number, and one
event for every decision and outcome the dashboard, the agent or the autopilot makes."""

import json
import re
from dataclasses import replace

import pytest
from fastapi.testclient import TestClient

from app import audit, campaign, evacuation, main, text_triage
from app.main import app
from app.providers import llm, routing, sms, voice, vonage
from app.state import state

client = TestClient(app)


def feature() -> dict:
    return {
        "type": "Feature",
        "geometry": {"type": "LineString", "coordinates": [[-4.4588, 40.3829], [-4.4652, 40.4552]]},
        "properties": {"summary": {"distance": 6_000, "duration": 600}, "segments": [{"steps": []}]},
    }


@pytest.fixture(autouse=True)
def fresh(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(evacuation, "_disk_cache", lambda: {})
    monkeypatch.setattr(evacuation, "_memory", {})
    monkeypatch.setattr(routing, "route_avoiding", lambda *_args, **_kw: feature())
    monkeypatch.setattr(main, "CALL_END_GRACE_S", 0)
    client.post("/api/reset")


def lines(log: audit.AuditLog) -> list[dict]:
    return [json.loads(line) for line in log._path.read_text(encoding="utf-8").splitlines()]


def actions(limit: int = 50) -> list[str]:
    return [event["action"] for event in client.get(f"/api/audit?limit={limit}").json()]


def first_neighbor() -> dict:
    return client.get("/api/neighbors").json()[0]


# --- The log itself -----------------------------------------------------------------------------


def test_events_are_appended_to_the_file_and_listed_newest_first(tmp_path) -> None:
    log = audit.AuditLog(tmp_path / "a.jsonl")
    log.record("autopilot.on", actor="coordinator")
    log.record("autopilot.off", actor="coordinator")
    assert [e["action"] for e in log.events()] == ["autopilot.off", "autopilot.on"]
    assert [e["action"] for e in lines(log)] == ["autopilot.on", "autopilot.off"]
    assert log.events(limit=1)[0]["action"] == "autopilot.off"


def test_a_restart_reads_the_file_back_from_its_last_reset(tmp_path) -> None:
    path = tmp_path / "a.jsonl"
    log = audit.AuditLog(path)
    log.record("autopilot.on", actor="coordinator")
    log.record(audit.RESET, actor="coordinator")
    log.record("call.ended", actor="coordinator", name="Ana")
    with path.open("a", encoding="utf-8") as file:
        file.write("not json\n")

    again = audit.AuditLog(path)
    assert [e["action"] for e in again.events()] == ["call.ended", audit.RESET]
    # The file keeps the whole trail.
    assert len(path.read_text(encoding="utf-8").splitlines()) == 4


def test_a_phone_number_is_never_written(tmp_path) -> None:
    log = audit.AuditLog(tmp_path / "a.jsonl")
    log.record("call.ended", actor="system", name="Ana", phone="+34 600 111 222", note="call me on 600111222")
    text = (tmp_path / "a.jsonl").read_text(encoding="utf-8")
    assert "600" not in text and "phone" not in text
    assert log.events()[0]["values"]["note"] == "call me on [redacted]"


def test_dates_and_ids_are_not_mistaken_for_phones() -> None:
    assert audit._clean({"at": "2026-07-23", "id": "a1b2c3d4", "count": 12}) == {
        "at": "2026-07-23",
        "id": "a1b2c3d4",
        "count": 12,
    }


def test_no_registry_phone_reaches_the_file_after_a_full_workflow(fresh_audit_log) -> None:
    neighbor = first_neighbor()
    zone = neighbor["zone"]
    order = next(o for o in client.get("/api/orders").json() if o["zone"] == zone)
    client.post(f"/api/orders/{zone}", json={"action": order["proposed_action"], "destination_id": order["proposed_destination_id"]})
    client.post("/tools/report_status", json={"neighbor_id": neighbor["id"], "status": "needs_rescue", "people": 2})
    client.post(f"/api/neighbors/{neighbor['id']}/call-ended")
    text = fresh_audit_log._path.read_text(encoding="utf-8")
    digits = re.sub(r"\D", "", text)
    for resident in state.neighbors():
        if resident.phone:
            assert re.sub(r"\D", "", resident.phone) not in digits


def test_the_api_renders_each_sentence_in_the_request_language() -> None:
    client.post("/api/autopilot", json={"enabled": True})
    english = client.get("/api/audit").json()
    spanish = client.get("/api/audit?lang=es").json()
    assert english[-1]["action"] == "demo.reset"
    on = next(e for e in english if e["action"] == "autopilot.on")
    assert on["message"] == "Call simulation turned on."
    assert next(e for e in spanish if e["action"] == "autopilot.on")["message"] == "Simulación de llamadas activada."


def test_the_limit_is_respected_and_the_export_is_a_download() -> None:
    for _ in range(3):
        client.post("/api/autopilot", json={"enabled": True})
        client.post("/api/autopilot", json={"enabled": False})
    assert len(client.get("/api/audit?limit=2").json()) == 2
    response = client.get("/api/audit/export")
    assert "attachment" in response.headers["content-disposition"]
    assert len(response.json()) >= 7


# --- Every decision and outcome ---------------------------------------------------------------


def test_an_approved_then_changed_order_is_logged() -> None:
    zone = first_neighbor()["zone"]
    order = next(o for o in client.get("/api/orders").json() if o["zone"] == zone)
    decision = {"action": "evacuate", "destination_id": order["proposed_destination_id"]}
    client.post(f"/api/orders/{zone}", json=decision)
    client.post(f"/api/orders/{zone}", json={"action": "shelter"})
    events = client.get("/api/audit").json()
    assert [e["action"] for e in events[:2]] == ["order.changedShelter", "order.approved"]
    assert order["zone_name"] in events[1]["message"] and events[1]["actor"] == "coordinator"


def test_status_reports_say_where_they_came_from(monkeypatch: pytest.MonkeyPatch) -> None:
    first, second, third = client.get("/api/neighbors").json()[:3]
    client.post("/tools/report_status", json={"neighbor_id": first["id"], "status": "evacuating"})
    client.post("/tools/report_status?via=dashboard", json={"neighbor_id": second["id"], "status": "no_answer"})
    monkeypatch.setattr(text_triage, "available", lambda: True)
    monkeypatch.setattr(llm, "chat", lambda *_a, **_k: json.dumps({"status": "evacuating", "people": 1}))
    client.post("/api/triage/text", json={"neighbor_id": third["id"], "text": "we are leaving"})
    reports = [e for e in client.get("/api/audit").json() if e["action"] == "status.reported"]
    assert [(e["subject"], e["source"], e["actor"]) for e in reports] == [
        (third["id"], "typed_answer", "coordinator"),
        (second["id"], "manual_button", "coordinator"),
        (first["id"], "agent_tool", "agent"),
    ]
    assert reports[2]["message"] == f"{first['name']}: evacuating, from the voice agent."


def test_the_safety_net_and_the_call_end_are_logged() -> None:
    neighbor = first_neighbor()
    client.post(f"/api/neighbors/{neighbor['id']}/call-ended")
    events = client.get("/api/audit").json()
    assert events[0]["action"] == "status.reported" and events[0]["source"] == "safety_net"
    assert events[1]["action"] == "call.ended"


def test_a_crew_alert_says_whether_it_is_texted(monkeypatch: pytest.MonkeyPatch) -> None:
    first, second = client.get("/api/neighbors").json()[:2]
    monkeypatch.setattr(sms, "configured", lambda: False)
    client.post("/tools/report_status", json={"neighbor_id": first["id"], "status": "needs_rescue"})
    assert actions()[0] == "alert.createdDashboard"

    sent: list[str] = []
    monkeypatch.setattr(sms, "configured", lambda: True)
    monkeypatch.setattr(sms, "send", lambda to, body: sent.append(body) or "SM1")
    monkeypatch.setattr(main, "settings", replace(main.settings, crew_phone="+34000"))
    client.post("/tools/report_status", json={"neighbor_id": second["id"], "status": "needs_rescue"})
    assert sent and actions()[:2] == ["alert.smsSent", "alert.createdSms"]


def test_closures_added_and_removed_are_logged() -> None:
    closure = client.post("/api/closures", json={"lat": 40.39, "lon": -4.44}).json()
    client.delete(f"/api/closures/{closure['id']}")
    events = client.get("/api/audit").json()
    assert [e["action"] for e in events[:2]] == ["closure.removed", "closure.added"]
    assert events[1]["subject"] == closure["id"] and "40.3900, -4.4400" in events[1]["message"]


def test_the_autopilot_on_off_and_what_it_scripted_are_logged() -> None:
    client.post("/api/replay/time", json={"at": "2026-07-23T22:00:00Z"})
    client.post("/api/autopilot", json={"enabled": True})
    scripted = [e for e in client.get("/api/audit?limit=100").json() if e["actor"] == "autopilot"]
    assert any(e["action"] == "status.reported" and e["source"] == "autopilot" for e in scripted)
    assert any(e["action"].startswith("order.approved") for e in scripted)
    client.post("/api/autopilot", json={"enabled": False})
    assert actions()[0] == "autopilot.off"


def test_a_video_link_is_logged_without_the_link(monkeypatch: pytest.MonkeyPatch) -> None:
    neighbor = first_neighbor()
    client.post("/tools/report_status", json={"neighbor_id": neighbor["id"], "status": "needs_rescue"})
    monkeypatch.setattr(vonage, "video_configured", lambda: True)
    monkeypatch.setattr(vonage, "sms_configured", lambda: True)
    monkeypatch.setattr(vonage, "create_session", lambda: "session-1")
    monkeypatch.setattr(vonage, "send_sms", lambda to, text: None)
    link = client.post(f"/api/rescues/{neighbor['id']}/video").json()
    event = client.get("/api/audit").json()[0]
    assert event["action"] == "video.linkTexted"
    assert link["link"] not in json.dumps(event)


def test_a_reset_starts_the_shown_log_again() -> None:
    client.post("/api/autopilot", json={"enabled": True})
    client.post("/api/reset")
    assert actions() == ["demo.reset"]


def test_a_campaign_and_its_calls_are_logged(monkeypatch: pytest.MonkeyPatch) -> None:
    zone = first_neighbor()["zone"]
    order = next(o for o in client.get("/api/orders").json() if o["zone"] == zone)
    client.post(f"/api/orders/{zone}", json={"action": "evacuate", "destination_id": order["proposed_destination_id"]})
    monkeypatch.setattr(voice, "phone_calls_configured", lambda: True)
    monkeypatch.setattr(voice, "call_resident", lambda phone, arguments: "call-1")
    monkeypatch.setattr(campaign, "watch", lambda calls: None)
    calls = client.post(f"/api/campaigns/{zone}").json()
    events = client.get("/api/audit?limit=100").json()
    assert events[0]["action"] == "campaign.started" and events[0]["values"]["count"] == len(calls)
    assert sum(e["action"] == "call.phoneStarted" for e in events) == len(calls)
