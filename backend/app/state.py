"""In-memory triage state. Good enough for the demo; swap for SQLite if needed."""

import json
import threading
from datetime import UTC, datetime
from pathlib import Path

from pydantic import ValidationError

from .i18n import t
from . import impact, scenario
from .config import settings
from .models import AgentFocus, CrewAlert, Neighbor, OrderDecision, ReportStatusRequest, Rescue, TriageStatus

def _registry_candidates() -> list:
    """Where the registry is read from, first found wins: HACKFIRE_NEIGHBORS_FILE, then the scenario's
    local registry (data/neighbors.local.json holds the team's real phone numbers and is git-ignored),
    then its tracked one."""
    files = scenario.current().files
    return [settings.neighbors_file, files.local_registry, files.registry]


def _build_registry(text: str, source: str) -> dict[str, Neighbor]:
    """The registry from JSON text, whether it came from HACKFIRE_NEIGHBORS_JSON or from a file.

    Errors name the source, the resident's position and the field, but never echo the input: it holds
    real phone numbers, and start-up errors end up in the deploy logs.
    """
    try:
        raw = json.loads(text)
    except json.JSONDecodeError as error:
        raise ValueError(f"{source} is not valid JSON ({error.msg}, line {error.lineno} column {error.colno})") from None
    if not isinstance(raw, list) or not raw:
        raise ValueError(f"{source} must be a non-empty list of residents")

    registry: dict[str, Neighbor] = {}
    for position, item in enumerate(raw, start=1):
        try:
            if not isinstance(item, dict):
                raise ValueError("expected an object")
            neighbor = Neighbor(**item)
        except ValidationError as error:
            problems = "; ".join(f"{'.'.join(str(part) for part in e['loc'])}: {e['msg']}" for e in error.errors())
            raise ValueError(f"{source}: resident {position} is invalid ({problems})") from None
        except ValueError as error:
            raise ValueError(f"{source}: resident {position} is invalid ({error})") from None
        if neighbor.id in registry:
            raise ValueError(f"{source}: resident {position} repeats the id {neighbor.id!r}")
        registry[neighbor.id] = neighbor
    return registry


class TriageState:
    def __init__(self) -> None:
        # The agent's tool calls and the call campaign's watcher write from different threads.
        self._lock = threading.RLock()
        self._neighbors: dict[str, Neighbor] = {}
        self._alerts: list[CrewAlert] = []
        # The coordinator's approved evacuation orders, by zone (orders.py).
        self.orders: dict[str, OrderDecision] = {}
        # The rescue the coordinator agent last asked the route for (#10).
        self.focus: AgentFocus | None = None
        # The replay moment the dashboard's slider is on; the agent answers for the same moment.
        self.replay_time: datetime | None = None
        self.load()

    def load(self) -> None:
        self._alerts = []
        self.orders = {}
        self.focus = None
        if settings.neighbors_json:
            self._neighbors = _build_registry(settings.neighbors_json, "HACKFIRE_NEIGHBORS_JSON")
            return
        for candidate in _registry_candidates():
            if candidate and Path(candidate).exists():
                self._neighbors = _build_registry(Path(candidate).read_text(encoding="utf-8"), Path(candidate).name)
                return
        self._neighbors = {}

    def neighbors(self) -> list[Neighbor]:
        return list(self._neighbors.values())

    def get(self, neighbor_id: str) -> Neighbor | None:
        return self._neighbors.get(neighbor_id)

    def find_by_address(self, address: str) -> Neighbor | None:
        wanted = " ".join(address.split()).casefold()
        return next((n for n in self._neighbors.values() if " ".join(n.address.split()).casefold() == wanted), None)

    def report(self, report: ReportStatusRequest) -> Neighbor | None:
        with self._lock:
            return self._report(report)

    def no_answer_if_pending(self, neighbor_id: str, observation: str | None = None) -> bool:
        """Mark a resident no_answer unless they already have a status, in one step. True if marked."""
        with self._lock:
            neighbor = self._neighbors.get(neighbor_id)
            if neighbor is not None and neighbor.status == TriageStatus.PENDING:
                self._report(
                    ReportStatusRequest(neighbor_id=neighbor_id, status=TriageStatus.NO_ANSWER, observation=observation)
                )
                return True
            return False

    def _report(self, report: ReportStatusRequest) -> Neighbor | None:
        neighbor = self._neighbors.get(report.neighbor_id)
        if neighbor is None:
            return None
        updated = neighbor.model_copy(
            update={
                "status": report.status,
                "people": report.people if report.people is not None else neighbor.people,
                "mobility": report.mobility or neighbor.mobility,
                "observation": report.observation or neighbor.observation,
                "updated_at": datetime.now(UTC),
            }
        )
        self._neighbors[updated.id] = updated
        if updated.status == TriageStatus.NEEDS_RESCUE and neighbor.status != TriageStatus.NEEDS_RESCUE:
            self._alerts.append(_crew_alert(updated))
        return updated

    def script(
        self,
        neighbor_id: str,
        status: TriageStatus,
        people: int | None,
        mobility: str | None,
        observation: str | None,
        at: datetime | None,
    ) -> None:
        """Set a resident as the demo autopilot's script says (autopilot.py), replacing the whole triage
        record so scrubbing back undoes it. A scripted rescue gets a crew alert on the dashboard only:
        nothing here texts anyone."""
        with self._lock:
            neighbor = self._neighbors.get(neighbor_id)
            if neighbor is None:
                return
            updated = neighbor.model_copy(
                update={"status": status, "people": people, "mobility": mobility, "observation": observation, "updated_at": at}
            )
            self._neighbors[neighbor_id] = updated
            alerted = any(alert.neighbor_id == neighbor_id for alert in self._alerts)
            if status != TriageStatus.NEEDS_RESCUE:
                self._alerts = [alert for alert in self._alerts if alert.neighbor_id != neighbor_id]
            elif not alerted:
                alert = _crew_alert(updated)
                self._alerts.append(alert.model_copy(update={"created_at": at or alert.created_at}))

    def snapshot(self) -> tuple:
        """Residents, alerts and orders as they are now, for `restore`."""
        with self._lock:
            return dict(self._neighbors), list(self._alerts), dict(self.orders)

    def restore(self, saved: tuple) -> None:
        with self._lock:
            neighbors, alerts, orders = saved
            self._neighbors, self._alerts, self.orders = dict(neighbors), list(alerts), dict(orders)

    def mark_alert_sent(self, rescue_id: str) -> None:
        self._alerts = [
            alert.model_copy(update={"sent_by_sms": True}) if alert.rescue_id == rescue_id else alert
            for alert in self._alerts
        ]

    def alerts(self) -> list[CrewAlert]:
        """Crew alerts, newest first. One per resident each time they become needs_rescue."""
        return list(reversed(self._alerts))

    def clock(self) -> datetime:
        """The replay moment every answer refers to: the slider's, or the scenario's until it moves.

        The scenario time (the scenario's `scenario_time`, or HACKFIRE_SCENARIO_TIME) is the moment
        the calls happen at, and the one the routes avoid the burned area of, so the agent's words and
        its routes agree.
        """
        moment = self.replay_time or scenario.current().scenario_time
        return moment if moment.tzinfo else moment.replace(tzinfo=UTC)

    def minutes_to_impact(self, zone: str) -> int | None:
        return impact.minutes_to_impact(zone, self.clock())

    def rescue_queue(self) -> list[Rescue]:
        minutes = {
            n.id: self.minutes_to_impact(n.zone)
            for n in self._neighbors.values()
            if n.status == TriageStatus.NEEDS_RESCUE
        }
        pending = [self._neighbors[neighbor_id] for neighbor_id in minutes]
        # Most urgent first: least time to impact, then the largest group.
        pending.sort(key=lambda n: (minutes[n.id] if minutes[n.id] is not None else 10**6, -(n.people or 1)))
        return [
            Rescue(
                rescue_id=f"rescue-{n.id}",
                neighbor=n,
                minutes_to_impact=minutes[n.id],
                priority=index + 1,
            )
            for index, n in enumerate(pending)
        ]


def crew_message(neighbor: Neighbor, link: str, locale: str | None = None) -> str:
    """The crew alert's text; the SMS goes in the crew's language, the dashboard reads it in its own."""
    people = t("crew.people", locale, count=neighbor.people) if neighbor.people else t("crew.peopleUnknown", locale)
    details = f"{people}, {neighbor.mobility}" if neighbor.mobility else people
    return t("crew.alert", locale, address=neighbor.address, details=details, link=link)


def _crew_alert(neighbor: Neighbor) -> CrewAlert:
    link = f"{settings.public_url}/?rescue={neighbor.id}"
    return CrewAlert(
        rescue_id=f"rescue-{neighbor.id}",
        neighbor_id=neighbor.id,
        message=crew_message(neighbor, link, settings.crew_locale),
        link=link,
        created_at=datetime.now(UTC),
    )


state = TriageState()
