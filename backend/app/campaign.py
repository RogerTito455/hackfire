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

from . import audit, briefing, orders
from .models import CampaignCall, TriageStatus
from .providers import voice
from .state import state

logger = logging.getLogger(__name__)

POLL_SECONDS = 5
# A call still going after this long is left alone.
WATCH_SECONDS = 15 * 60

# Calls in progress: neighbor id to SLNG call id.
_active: dict[str, str] = {}
_active_lock = threading.Lock()


class NotApproved(Exception):
    """The zone's order is not approved, so nobody in it may be called."""


class NoPhoneLine(Exception):
    """No outbound trunk is set up (HACKFIRE_PHONE_CALLS is off)."""


class Unknown(Exception):
    """No resident with that id."""


class AlreadyCalling(Exception):
    """This resident's phone is already ringing."""


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
            call_id = voice.call_resident(resident.phone, briefing.call_variables(resident))
        except voice.VoiceUnavailable as error:
            logger.warning("SLNG refused the call to %s: %s", resident.id, error)
            if state.no_answer_if_pending(resident.id):
                audit.status_reported(state.get(resident.id), source="campaign", actor="system")
            calls.append(CampaignCall(neighbor_id=resident.id, call_id=None))
            continue
        with _active_lock:
            _active[resident.id] = call_id
        audit.record("call.phoneStarted", actor="system", source="campaign", subject=resident.id, name=resident.name)
        calls.append(CampaignCall(neighbor_id=resident.id, call_id=call_id))
    return calls


def call_one(neighbor_id: str) -> CampaignCall:
    """Ring one resident now, whatever their triage status.

    What a campaign does for a whole zone, for a single phone: the button the coordinator presses
    on stage, and in a rehearsal, when dialling everyone is more than the moment needs. A
    campaign's guards stay: a phone line, the zone's order approved, and never two calls to the
    same person at once. Unlike a campaign, someone who already answered can be rung again,
    because a rehearsal repeats.
    """
    if not voice.phone_calls_configured():
        raise NoPhoneLine
    resident = state.get(neighbor_id)
    if resident is None:
        raise Unknown
    if orders.approved_order(resident.zone) is None:
        raise NotApproved
    with _active_lock:
        active = _active.get(neighbor_id)
    if active is not None:
        # The last call may be over without the watcher having noticed yet: a poll that failed, a
        # redeploy, a watch that timed out. Ask SLNG before refusing, so the button is never stuck
        # for fifteen minutes on stage. If SLNG cannot say, dial: a second ring beats a dead button.
        try:
            still_up = not voice.call_ended(active)
        except voice.VoiceUnavailable:
            still_up = False
        if still_up:
            raise AlreadyCalling
        with _active_lock:
            if _active.get(neighbor_id) == active:
                del _active[neighbor_id]
    try:
        call_id = voice.call_resident(resident.phone, briefing.call_variables(resident))
    except voice.VoiceUnavailable as error:
        logger.warning("SLNG refused the call to %s: %s", resident.id, error)
        if state.no_answer_if_pending(resident.id):
            audit.status_reported(state.get(resident.id), source="campaign", actor="system")
        return CampaignCall(neighbor_id=resident.id, call_id=None)
    with _active_lock:
        _active[resident.id] = call_id
    audit.record("call.phoneStarted", actor="system", source="campaign", subject=resident.id, name=resident.name)
    return CampaignCall(neighbor_id=resident.id, call_id=call_id)


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
                audit.record("call.ended", actor="system", source="campaign", subject=neighbor_id, name=audit.resident_name(neighbor_id))
                if state.no_answer_if_pending(neighbor_id):
                    audit.status_reported(state.get(neighbor_id), source="campaign", actor="system")
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
