"""In-memory triage state. Good enough for the demo; swap for SQLite if needed."""

import json
from datetime import UTC, datetime
from pathlib import Path

from . import zones
from .config import DATA_DIR, settings
from .models import CrewAlert, Neighbor, ReportStatusRequest, Rescue, TriageStatus

# neighbors.local.json holds the team's real phone numbers and is git-ignored.
_REGISTRY_CANDIDATES = [
    settings.neighbors_file,
    DATA_DIR / "neighbors.local.json",
    DATA_DIR / "neighbors.sample.json",
]



class TriageState:
    def __init__(self) -> None:
        self._neighbors: dict[str, Neighbor] = {}
        self._alerts: list[CrewAlert] = []
        self.load()

    def load(self) -> None:
        self._alerts = []
        for candidate in _REGISTRY_CANDIDATES:
            if candidate and Path(candidate).exists():
                raw = json.loads(Path(candidate).read_text(encoding="utf-8"))
                self._neighbors = {n["id"]: Neighbor(**n) for n in raw}
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

    def alerts(self) -> list[CrewAlert]:
        """Crew alerts, newest first. One per resident each time they become needs_rescue."""
        return list(reversed(self._alerts))

    def minutes_to_impact(self, zone: str) -> int | None:
        """From the predicted spread at the scenario time (spread.py, zones.py)."""
        return zones.minutes_to_impact(zone, settings.scenario_time)

    def rescue_queue(self) -> list[Rescue]:
        pending = [n for n in self._neighbors.values() if n.status == TriageStatus.NEEDS_RESCUE]
        # Most urgent first: least time to impact, then the largest group.
        pending.sort(
            key=lambda n: (
                self.minutes_to_impact(n.zone) if self.minutes_to_impact(n.zone) is not None else 10**6,
                -(n.people or 1),
            )
        )
        return [
            Rescue(
                rescue_id=f"rescue-{n.id}",
                neighbor=n,
                minutes_to_impact=self.minutes_to_impact(n.zone),
                priority=index + 1,
            )
            for index, n in enumerate(pending)
        ]


def _crew_alert(neighbor: Neighbor) -> CrewAlert:
    link = f"{settings.public_url}/?rescue={neighbor.id}"
    people = f"{neighbor.people} people" if neighbor.people else "Number of people unknown"
    details = f"{people}, {neighbor.mobility}" if neighbor.mobility else people
    return CrewAlert(
        rescue_id=f"rescue-{neighbor.id}",
        neighbor_id=neighbor.id,
        message=f"Rescue needed at {neighbor.address}. {details}. Route: {link}",
        link=link,
        created_at=datetime.now(UTC),
    )


state = TriageState()
