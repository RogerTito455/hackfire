"""The audit log: every decision and outcome, append-only, without a database.

Each event is one JSON object per line in HACKFIRE_AUDIT_FILE (data/audit.jsonl, git-ignored) and in
memory. An event stores what happened as a locale key and its values, never text, so the dashboard
reads each sentence in its own language (app/locales, "audit" section). It names residents by name and
id only: a value that looks like a phone number is blanked before it is written, and a `phone` value is
never written at all.

A demo reset does not touch the file. It appends a `demo.reset` event, and the log shows the events
from the last reset on; on start-up the file is read back from its last reset. The file is the whole
trail, the dashboard the current run. See docs/setup/operations.md.
"""

import json
import logging
import re
import threading
import uuid
from datetime import UTC, datetime
from pathlib import Path

from .config import settings
from .i18n import t

logger = logging.getLogger(__name__)

RESET = "demo.reset"

# Nine digits or more, spaced or not, with or without a + or 00 prefix: a phone number, not an id or a date.
_PHONE = re.compile(r"(?:\+|00)?\d(?:[\s.-]?\d){8,}")
_FORBIDDEN_KEYS = {"phone", "phone_number", "to", "number"}

Value = str | int | float | bool | None


def _clean(values: dict[str, object]) -> dict[str, Value]:
    """The values safe to write: no phone key, no phone-shaped text, only plain JSON scalars."""
    clean: dict[str, Value] = {}
    for key, value in values.items():
        if key in _FORBIDDEN_KEYS:
            continue
        if isinstance(value, str):
            value = _PHONE.sub("[redacted]", value)
        elif value is not None and not isinstance(value, (int, float, bool)):
            value = _PHONE.sub("[redacted]", str(value))
        clean[key] = value
    return clean


class AuditLog:
    def __init__(self, path: Path | None) -> None:
        self._path = path
        self._lock = threading.Lock()
        self._events: list[dict] = []
        self._load()

    def _load(self) -> None:
        """The events from the file's last reset on. A line that is not JSON is skipped."""
        if self._path is None or not self._path.exists():
            return
        events = []
        try:
            lines = self._path.read_text(encoding="utf-8").splitlines()
        except OSError as error:
            logger.warning("could not read the audit log: %s", error)
            return
        for line in lines:
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(event, dict) or "action" not in event:
                continue
            if event["action"] == RESET:
                events = []
            events.append(event)
        self._events = events

    def record(
        self,
        action: str,
        *,
        actor: str,
        source: str | None = None,
        subject: str | None = None,
        at: datetime | None = None,
        **values: object,
    ) -> dict:
        """Append one event. `action` names its sentence (audit.<action> in app/locales)."""
        event = {
            "id": uuid.uuid4().hex[:12],
            "at": (at or datetime.now(UTC)).isoformat(),
            "action": action,
            "actor": actor,
            "source": source,
            "subject": subject,
            "values": _clean(values),
        }
        with self._lock:
            if action == RESET:
                self._events = []
            self._events.append(event)
            if self._path is not None:
                try:
                    self._path.parent.mkdir(parents=True, exist_ok=True)
                    with self._path.open("a", encoding="utf-8") as file:
                        file.write(json.dumps(event, ensure_ascii=False) + "\n")
                except OSError as error:
                    # The event stays in memory; the dashboard still shows it.
                    logger.warning("could not write the audit log: %s", error)
        return event

    def events(self, limit: int | None = None) -> list[dict]:
        """The current run's events, newest first."""
        with self._lock:
            newest = list(reversed(self._events))
        return newest if limit is None else newest[:limit]


def message(event: dict, locale: str | None = None) -> str:
    """The event's sentence in the request's language."""
    values = dict(event.get("values") or {})
    if isinstance(values.get("status"), str):
        values["status"] = _label("audit.statuses", values["status"], locale)
    source = event.get("source")
    if source:
        values["source"] = _label("audit.sources", source, locale)
    try:
        return t(f"audit.{event['action']}", locale, **values)
    except KeyError:
        return event["action"]


def _label(section: str, key: str, locale: str | None) -> str:
    try:
        return t(f"{section}.{key}", locale)
    except KeyError:
        return key


log = AuditLog(settings.audit_file)


def record(action: str, **kwargs) -> dict:
    """Append to the process's log (a function, so tests can swap `log`)."""
    return log.record(action, **kwargs)


# --- What main.py and campaign.py log --------------------------------------------------------
# Imports inside the functions: state and orders load the scenario, and this module stays light.


def resident_name(neighbor_id: str) -> str:
    from .state import state

    neighbor = state.get(neighbor_id)
    return neighbor.name if neighbor is not None else neighbor_id


def status_reported(neighbor, *, source: str, actor: str) -> None:
    """A resident's triage status was recorded. `source`: agent_tool, typed_answer, manual_button,
    autopilot, safety_net or campaign."""
    if neighbor is None:
        return
    record(
        "status.reported",
        actor=actor,
        source=source,
        subject=neighbor.id,
        name=neighbor.name,
        status=str(neighbor.status),
        people=neighbor.people,
    )


def order_decided(order, *, changed: bool, actor: str, source: str) -> None:
    shelter = str(order.action) == "shelter"
    action = ("order.changed" if changed else "order.approved") + ("Shelter" if shelter else "")
    record(
        action,
        actor=actor,
        source=source,
        subject=order.zone,
        zone=order.zone_name,
        destination=order.destination_name,
    )


def autopilot_changes(before: tuple, after: tuple) -> None:
    """What one move of the demo autopilot changed (state.snapshot() before and after): orders it
    approved, residents it gave a status, crew alerts it raised. Scrubbing back is not logged."""
    from . import orders

    neighbors_before, alerts_before, orders_before = before
    neighbors_after, alerts_after, orders_after = after
    new_zones = [zone for zone in orders_after if zone not in orders_before]
    if new_zones:
        for order in orders.orders():
            if order.zone in new_zones:
                order_decided(order, changed=False, actor="autopilot", source="autopilot")
    for neighbor_id, neighbor in neighbors_after.items():
        previous = neighbors_before.get(neighbor_id)
        if str(neighbor.status) != "pending" and (previous is None or previous.status != neighbor.status):
            status_reported(neighbor, source="autopilot", actor="autopilot")
    known = {alert.rescue_id for alert in alerts_before}
    for alert in alerts_after:
        if alert.rescue_id not in known:
            record(
                "alert.createdDashboard",
                actor="autopilot",
                source="autopilot",
                subject=alert.neighbor_id,
                name=resident_name(alert.neighbor_id),
            )
