"""Demo autopilot: a labelled simulation of the coordinator's workflow along the replay. Off by default.

With it on, every move of the replay clock sets the demo residents' triage and the zones' orders from a
fixed script, data/demo_timeline.json: orders approved, residents evacuating, one not answering, one
needing rescue, a retry. Each scripted resident takes the latest outcome at or before the clock, or goes
back to pending, so scrubbing back undoes. It is a simulation with the demo residents, not what happened
on 23 July 2026.

It never places a call, starts a campaign or sends an SMS. It writes the dashboard's state directly
(`state.script`), never through /tools/report_status, which is the only path that texts the crew, so a
scripted rescue's crew alert stays on the dashboard. Turning it off puts back the residents, orders and
alerts as they were before it was turned on; a demo reset turns it off.
"""

import json
import threading
from dataclasses import dataclass
from datetime import datetime
from functools import cache

from . import orders
from .config import DATA_DIR
from .i18n import t
from .models import Neighbor, OrderDecision, TriageStatus
from .state import state

TIMELINE_FILE = DATA_DIR / "demo_timeline.json"



def _note(key: str | None) -> str | None:
    """A scripted note, named by its key in the "demo" section of backend/app/locales, written in the
    language of the dashboard that moved the slider. A note that is not a key is kept as written."""
    if not key:
        return None
    try:
        return t(f"demo.{key}")
    except KeyError:
        return key

@dataclass(frozen=True)
class Outcome:
    at: datetime
    position: int  # 1-based, in the registry's order
    status: TriageStatus
    people: int | None = None
    mobility: str | None = None
    observation: str | None = None


@dataclass(frozen=True)
class OrderEvent:
    at: datetime
    zone_of: int  # the position of a resident whose zone the order is for


@dataclass(frozen=True)
class Timeline:
    orders: tuple[OrderEvent, ...]
    outcomes: tuple[Outcome, ...]


@dataclass(frozen=True)
class Plan:
    """What the script says at one moment: each scripted resident's outcome (None: pending) and
    whether each scripted zone's order is approved."""

    outcomes: dict[str, Outcome | None]
    zones: dict[str, bool]


def parse(raw: dict) -> Timeline:
    return Timeline(
        orders=tuple(
            OrderEvent(at=datetime.fromisoformat(e["at"]), zone_of=int(e["zone_of"])) for e in raw.get("orders", [])
        ),
        outcomes=tuple(
            Outcome(
                at=datetime.fromisoformat(e["at"]),
                position=int(e["position"]),
                status=TriageStatus(e["status"]),
                people=e.get("people"),
                mobility=e.get("mobility"),
                observation=e.get("observation"),
            )
            for e in raw.get("outcomes", [])
        ),
    )


@cache
def timeline() -> Timeline:
    return parse(json.loads(TIMELINE_FILE.read_text(encoding="utf-8")))


def plan(script: Timeline, residents: list[Neighbor], at: datetime) -> Plan:
    """The script at `at` for this registry. Pure. Positions the registry does not have are skipped.

    A zone's order counts as approved from its order event, or from the first scripted outcome of a
    resident in it, whichever comes first: nobody is called before their zone's order.
    """
    by_position = {index: resident for index, resident in enumerate(residents, start=1)}
    outcomes: dict[str, Outcome | None] = {}
    approved_from: dict[str, datetime] = {}
    for outcome in sorted(script.outcomes, key=lambda o: o.at):
        resident = by_position.get(outcome.position)
        if resident is None:
            continue
        outcomes.setdefault(resident.id, None)
        if outcome.at <= at:
            outcomes[resident.id] = outcome
        approved_from[resident.zone] = min(approved_from.get(resident.zone, outcome.at), outcome.at)
    for event in script.orders:
        resident = by_position.get(event.zone_of)
        if resident is not None:
            approved_from[resident.zone] = min(approved_from.get(resident.zone, event.at), event.at)
    return Plan(outcomes=outcomes, zones={zone: start <= at for zone, start in approved_from.items()})


# The state from before the autopilot was turned on; None while it is off.
_saved: tuple | None = None
_lock = threading.Lock()


def enabled() -> bool:
    return _saved is not None


def turn_on(at: datetime) -> None:
    global _saved
    with _lock:
        if _saved is None:
            _saved = state.snapshot()
    follow(at)


def turn_off() -> None:
    global _saved
    with _lock:
        if _saved is not None:
            state.restore(_saved)
        _saved = None


def forget() -> None:
    """A demo reset reloads the state itself: just drop the autopilot and its saved state."""
    global _saved
    with _lock:
        _saved = None


def follow(at: datetime) -> None:
    """Set the scripted residents and orders to what the script says at `at`. No-op while off."""
    with _lock:
        if _saved is None:
            return
        now = plan(timeline(), state.neighbors(), at)
        for zone, approved in now.zones.items():
            if not approved:
                state.orders.pop(zone, None)
            elif zone not in state.orders:
                proposal = next((o for o in orders.orders() if o.zone == zone), None)
                if proposal is not None:
                    state.orders[zone] = OrderDecision(
                        action=proposal.proposed_action, destination_id=proposal.proposed_destination_id
                    )
        # Oldest outcome first, so crew alerts keep the script's order.
        for neighbor_id, outcome in sorted(now.outcomes.items(), key=lambda item: item[1].at if item[1] else at):
            if outcome is None:
                state.script(neighbor_id, TriageStatus.PENDING, None, None, None, None)
            else:
                state.script(
                    neighbor_id, outcome.status, outcome.people, _note(outcome.mobility), _note(outcome.observation), outcome.at
                )
