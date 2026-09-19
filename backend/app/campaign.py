"""Call campaigns (#8): once the coordinator approves a zone's order, the agent phones its residents.

Nothing is dialled for a zone whose order is not approved, and nobody is dialled twice at once:
residents who already have a triage status, or a call still going, are skipped. One watcher follows
a campaign's calls until each ends; a resident still pending by then did not answer (or the call
failed) and becomes no_answer. What a resident told the agent is never overwritten. A call SLNG
refuses to place counts as unanswered. A demo reset forgets the calls in progress.
"""

import logging
import threading
import time

from . import briefing, evacuation, orders
from .models import CampaignCall, Neighbor, TravelMode, TriageStatus
from .providers import voice
from .state import state

logger = logging.getLogger(__name__)

POLL_SECONDS = 5
# A call still going after this long is left alone.
WATCH_SECONDS = 15 * 60

# Calls in progress: neighbor id to SLNG call id.
_active: dict[str, str] = {}
_active_lock = threading.Lock()


def call_variables(neighbor: Neighbor) -> dict[str, str]:
    """The resident agent's call variables (voice/resident/agent.yaml), for a call or a web session.

    Besides who and where, the agent starts knowing the fire, the order and the route by car, so it
    opens with them instead of calling a tool while the resident waits. An empty route leaves the
    agent to ask for one (get_evacuation_route) when it is needed.
    """
    try:
        route = orders.route_for(neighbor, TravelMode.CAR).spoken_directions
    except evacuation.RoutingUnavailable:
        route = ""
    return {
        "neighbor_id": neighbor.id,
        "resident_name": neighbor.name,
        "address": neighbor.address,
        "zone": neighbor.zone,
        "fire_status": briefing.fire_summary(neighbor.zone),
        "route": route,
    }


class NotApproved(Exception):
    """The zone's order is not approved, so nobody in it may be called."""


class NoPhoneLine(Exception):
    """No outbound trunk is set up (HACKFIRE_PHONE_CALLS is off)."""


def start(zone: str) -> list[CampaignCall]:
    if not voice.phone_calls_configured():
        raise NoPhoneLine
    if orders.approved_order(zone) is None:
        raise NotApproved
    calls = []
    for resident in state.neighbors():
        if resident.zone != zone or resident.status != TriageStatus.PENDING:
            continue
        with _active_lock:
            if resident.id in _active:
                continue
        try:
            call_id = voice.call_resident(resident.phone, call_variables(resident))
        except voice.VoiceUnavailable as error:
            logger.warning("SLNG refused the call to %s: %s", resident.id, error)
            state.no_answer_if_pending(resident.id)
            calls.append(CampaignCall(neighbor_id=resident.id, call_id=None))
            continue
        with _active_lock:
            _active[resident.id] = call_id
        calls.append(CampaignCall(neighbor_id=resident.id, call_id=call_id))
    return calls


def watch(calls: list[CampaignCall]) -> None:
    """Follow a campaign's calls, all at once, until each ends or the watch times out."""
    waiting = {c.neighbor_id: c.call_id for c in calls if c.call_id is not None}
    deadline = time.monotonic() + WATCH_SECONDS
    while waiting and time.monotonic() <= deadline:
        for neighbor_id, call_id in list(waiting.items()):
            with _active_lock:
                if _active.get(neighbor_id) != call_id:  # forgotten by a reset
                    del waiting[neighbor_id]
                    continue
            if _ended(call_id):
                del waiting[neighbor_id]
                with _active_lock:
                    _active.pop(neighbor_id, None)
                state.no_answer_if_pending(neighbor_id)
        if waiting:
            time.sleep(POLL_SECONDS)
    with _active_lock:
        for neighbor_id, call_id in waiting.items():
            if _active.get(neighbor_id) == call_id:
                del _active[neighbor_id]


def forget() -> None:
    """Drop every call in progress, so a reset demo starts clean."""
    with _active_lock:
        _active.clear()


def _ended(call_id: str) -> bool:
    try:
        return voice.call_ended(call_id)
    except voice.VoiceUnavailable:
        return False  # Ask again on the next poll.
