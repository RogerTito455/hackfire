"""Demo autopilot: a labelled simulation of the coordinator's workflow along the replay. Off by default.

With it on, every move of the replay clock sets the demo residents' triage and the zones' orders from a
script, data/demo_timeline.json, timed by the forecast: a zone's order is approved a set number of
minutes after the zone first enters the predicted spread (impact.py), and each scripted resident's call
lands a set number of minutes after their zone's order. Outcomes are named by registry position:
residents evacuating, one not answering, one needing rescue, a retry. Each scripted resident takes the
latest outcome at or before the clock, or goes back to pending, so scrubbing back undoes. It is a
simulation with the demo residents, not what happened in the replayed fire. The script and the recorded
calls are the active scenario's (scenario.py).

Each scripted outcome also names a transcript from data/demo_calls.json: a real call of the resident
agent with a resident simulated by Galtea, with the same status. The dashboard types it out when the
outcome lands. When a scripted rescue lands, the agent focus points at it, so the dashboard draws the
crew's route as it does for the coordinator agent.

It never places a call, starts a campaign or sends an SMS. It writes the dashboard's state directly
(`state.script`), never through /tools/report_status, which is the only path that texts the crew, so a
scripted rescue's crew alert stays on the dashboard. Turning it off puts back the residents, orders,
alerts and focus as they were before it was turned on; a demo reset turns it off.
"""

import json
import threading
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from . import impact, orders
from .i18n import t
from .models import (
    AgentFocus,
    AutopilotCall,
    AutopilotTranscript,
    AutopilotTurn,
    Neighbor,
    OrderDecision,
    TriageStatus,
)
from .scenario import cached, current
from .state import state


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
    after: timedelta  # after the resident's zone's order is approved
    position: int  # 1-based, in the registry's order
    status: TriageStatus
    people: int | None = None
    mobility: str | None = None
    observation: str | None = None


@dataclass(frozen=True)
class OrderEvent:
    after: timedelta  # after the zone first enters the forecast
    zone_of: int  # the position of a resident whose zone the order is for


@dataclass(frozen=True)
class Timeline:
    order_after: timedelta  # for a scripted zone no order event names
    orders: tuple[OrderEvent, ...]
    outcomes: tuple[Outcome, ...]
    # Transcript keys by status: the n-th scripted outcome of a status takes the n-th key, cycling.
    calls: Mapping[str, tuple[str, ...]]


@dataclass(frozen=True)
class ScheduledCall:
    """A scripted outcome on the replay clock, for one resident of this registry."""

    at: datetime
    neighbor_id: str
    outcome: Outcome
    transcript: str | None


@dataclass(frozen=True)
class Schedule:
    orders: dict[str, datetime]  # zone -> when its order is approved
    calls: tuple[ScheduledCall, ...]  # oldest first


@dataclass(frozen=True)
class Plan:
    """What the script says at one moment: each scripted resident's latest call (None: pending) and
    whether each scripted zone's order is approved."""

    outcomes: dict[str, ScheduledCall | None]
    zones: dict[str, bool]


def _minutes(value: object) -> timedelta:
    return timedelta(minutes=float(value))  # type: ignore[arg-type]


def parse(raw: dict) -> Timeline:
    return Timeline(
        order_after=_minutes(raw.get("order_after_minutes", 0)),
        orders=tuple(
            OrderEvent(after=_minutes(e["after_minutes"]), zone_of=int(e["zone_of"])) for e in raw.get("orders", [])
        ),
        outcomes=tuple(
            Outcome(
                after=_minutes(e["after_minutes"]),
                position=int(e["position"]),
                status=TriageStatus(e["status"]),
                people=e.get("people"),
                mobility=e.get("mobility"),
                observation=e.get("observation"),
            )
            for e in raw.get("outcomes", [])
        ),
        calls={status: tuple(keys) for status, keys in (raw.get("calls") or {}).items()},
    )


@cached
def timeline() -> Timeline:
    return parse(json.loads(current().files.timeline.read_text(encoding="utf-8")))


def parse_transcripts(raw: dict) -> dict[str, AutopilotTranscript]:
    """The recorded calls that have a status and at least one turn, by scenario key."""
    transcripts = {}
    for key, call in (raw.get("calls") or {}).items():
        if call.get("status") and call.get("turns"):
            transcripts[key] = AutopilotTranscript(
                scenario=key,
                status=TriageStatus(call["status"]),
                turns=[AutopilotTurn(speaker=turn["speaker"], text=turn["text"]) for turn in call["turns"]],
            )
    return transcripts


@cached
def transcripts() -> dict[str, AutopilotTranscript]:
    path = current().files.calls
    if not path.exists():
        return {}
    return parse_transcripts(json.loads(path.read_text(encoding="utf-8")))


def assign_transcripts(
    script: Timeline, recorded: Mapping[str, AutopilotTranscript]
) -> list[str | None]:
    """One transcript key per scripted outcome, in the script's order. Pure.

    The n-th outcome of a status takes the n-th key the script lists for that status, cycling. A key
    whose recording is missing or recorded another status is never used: the card must show a call
    that ended the way the pin did."""
    usable = {
        status: [key for key in keys if key in recorded and recorded[key].status == status]
        for status, keys in script.calls.items()
    }
    seen: dict[str, int] = {}
    assigned: list[str | None] = []
    for outcome in script.outcomes:
        keys = usable.get(outcome.status.value) or []
        index = seen.get(outcome.status.value, 0)
        seen[outcome.status.value] = index + 1
        assigned.append(keys[index % len(keys)] if keys else None)
    return assigned


def first_in_forecast(zone: str) -> datetime | None:
    """The first replay moment the forecast gives this zone a time to impact, or None if it never does."""
    return next(
        (f.issued_at for f in impact.forecasts() if impact.minutes_to_impact(zone, f.issued_at) is not None), None
    )


def schedule(
    script: Timeline,
    residents: list[Neighbor],
    entries: Mapping[str, datetime | None],
    recorded: Mapping[str, AutopilotTranscript] | None = None,
) -> Schedule:
    """The script on the replay clock for this registry. Pure: `entries` gives each zone's first moment
    in the forecast. Positions the registry does not have, and residents of a zone the forecast never
    reaches, are skipped: the calls follow the fire."""
    by_position = {index: resident for index, resident in enumerate(residents, start=1)}
    in_forecast = {r.zone: entries.get(r.zone) for r in residents if entries.get(r.zone) is not None}

    ordered_after: dict[str, timedelta] = {}
    for event in script.orders:
        resident = by_position.get(event.zone_of)
        if resident is not None and resident.zone in in_forecast:
            ordered_after[resident.zone] = min(ordered_after.get(resident.zone, event.after), event.after)

    order_at: dict[str, datetime] = {}
    calls: list[ScheduledCall] = []
    for outcome, transcript in zip(script.outcomes, assign_transcripts(script, recorded or {}), strict=True):
        resident = by_position.get(outcome.position)
        if resident is None or resident.zone not in in_forecast:
            continue
        # Nobody is called before their zone's order: a zone with a call gets one.
        zone_order = order_at.setdefault(
            resident.zone, in_forecast[resident.zone] + ordered_after.get(resident.zone, script.order_after)
        )
        calls.append(ScheduledCall(zone_order + outcome.after, resident.id, outcome, transcript))
    for zone, after in ordered_after.items():
        order_at.setdefault(zone, in_forecast[zone] + after)
    return Schedule(orders=order_at, calls=tuple(sorted(calls, key=lambda c: c.at)))


def plan(plan_schedule: Schedule, at: datetime) -> Plan:
    """The schedule at `at`. Pure."""
    outcomes: dict[str, ScheduledCall | None] = {}
    for call in plan_schedule.calls:
        outcomes.setdefault(call.neighbor_id, None)
        if call.at <= at:
            outcomes[call.neighbor_id] = call
    return Plan(outcomes=outcomes, zones={zone: start <= at for zone, start in plan_schedule.orders.items()})


def current_schedule() -> Schedule:
    residents = state.neighbors()
    entries = {zone: first_in_forecast(zone) for zone in {r.zone for r in residents}}
    return schedule(timeline(), residents, entries, transcripts())


def calls() -> list[AutopilotCall]:
    """The scripted outcomes for the dashboard's call card: empty while the autopilot is off."""
    if not enabled():
        return []
    return [
        AutopilotCall(neighbor_id=c.neighbor_id, at=c.at, status=c.outcome.status, transcript=c.transcript)
        for c in current_schedule().calls
    ]


def used_transcripts() -> dict[str, AutopilotTranscript]:
    named = {call.transcript for call in calls() if call.transcript}
    return {key: value for key, value in transcripts().items() if key in named}


# The state and agent focus from before the autopilot was turned on; None while it is off.
# Norma global keyword used inside a function: the state the demo autopilot has to put back when it is
# turned off, rebound under `_lock`. This module drives the demo and is deliberately left as it is.
_saved: tuple | None = None
_lock = threading.Lock()


def enabled() -> bool:
    return _saved is not None


def turn_on(at: datetime) -> None:
    global _saved
    with _lock:
        if _saved is None:
            _saved = (state.snapshot(), state.focus)
    follow(at)


def turn_off() -> None:
    global _saved
    with _lock:
        if _saved is not None:
            snapshot, focus = _saved
            state.restore(snapshot)
            state.focus = focus
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
        now = plan(current_schedule(), at)
        for zone, approved in now.zones.items():
            if not approved:
                state.orders.pop(zone, None)
            elif zone not in state.orders:
                proposal = next((o for o in orders.orders() if o.zone == zone), None)
                if proposal is not None:
                    state.orders[zone] = OrderDecision(
                        action=proposal.proposed_action, destination_id=proposal.proposed_destination_id
                    )
        # Oldest outcome first, so crew alerts keep the script's order and the newest rescue has the focus.
        for neighbor_id, call in sorted(now.outcomes.items(), key=lambda item: item[1].at if item[1] else at):
            before = state.get(neighbor_id)
            if call is None:
                state.script(neighbor_id, TriageStatus.PENDING, None, None, None, None)
            else:
                outcome = call.outcome
                state.script(
                    neighbor_id, outcome.status, outcome.people, _note(outcome.mobility), _note(outcome.observation), call.at
                )
            _follow_rescue(neighbor_id, before, call)


def _follow_rescue(neighbor_id: str, before: Neighbor | None, call: ScheduledCall | None) -> None:
    """A rescue that just landed takes the agent focus, so the dashboard draws the crew's route to it
    (useFollowAgent); scrubbing back before it lets go of the focus."""
    rescue = call is not None and call.outcome.status == TriageStatus.NEEDS_RESCUE
    was_rescue = before is not None and before.status == TriageStatus.NEEDS_RESCUE
    if rescue and not was_rescue:
        state.focus = AgentFocus(neighbor_id=neighbor_id, rescue_id=f"rescue-{neighbor_id}", at=datetime.now(UTC))
    elif not rescue and state.focus is not None and state.focus.neighbor_id == neighbor_id:
        state.focus = None
