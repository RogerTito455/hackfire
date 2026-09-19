"""In-memory triage state. Good enough for the demo; swap for SQLite if needed."""

import json
from datetime import UTC, datetime
from pathlib import Path

from . import impact
from .config import DATA_DIR, settings
from .models import Neighbor, ReportStatusRequest, Rescue, TriageStatus

# neighbors.local.json holds the team's real phone numbers and is git-ignored.
_REGISTRY_CANDIDATES = [
    settings.neighbors_file,
    DATA_DIR / "neighbors.local.json",
    DATA_DIR / "neighbors.sample.json",
]

try:
    _DEMO_TIME = datetime.fromisoformat(settings.demo_time)
except ValueError as error:
    raise ValueError(
        f"HACKFIRE_DEMO_TIME must be an ISO 8601 time such as 2026-07-23T15:00:00Z, got {settings.demo_time!r}"
    ) from error
if _DEMO_TIME.tzinfo is None:
    _DEMO_TIME = _DEMO_TIME.replace(tzinfo=UTC)


class TriageState:
    def __init__(self) -> None:
        self._neighbors: dict[str, Neighbor] = {}
        # The replay moment the dashboard's slider is on; the agent answers for the same moment.
        self.replay_time: datetime | None = None
        self.load()

    def load(self) -> None:
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
        return updated

    def clock(self) -> datetime:
        """The replay moment every answer refers to: the slider's, or the demo's until it moves."""
        return self.replay_time or _DEMO_TIME

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


state = TriageState()
