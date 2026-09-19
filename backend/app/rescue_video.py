"""Live video from a resident who needs rescue (#18): the coordinator asks, the resident opens a link.

The coordinator asks for video from a resident in the rescue queue; the resident gets an SMS with a
single-use link that opens their camera in the browser, no app to install, and the coordinator's
dashboard shows the stream next to their pin, with captions in Spanish. One routed Vonage session per
resident. In memory, like the triage state; a demo reset forgets it.
"""

import logging
import secrets

from .config import settings
from .i18n import t
from .models import RescueVideo, RescueVideoLink, TriageStatus, VideoAccess
from .providers import vonage
from .state import state

logger = logging.getLogger(__name__)

CAPTIONS_LANGUAGE = "es-ES"
# A resident's camera token lasts long enough for the rescue to arrive; the coordinator's, a shift.
PUBLISHER_TTL_S = 60 * 60
SUBSCRIBER_TTL_S = 4 * 60 * 60

# Session per resident; single-use links, link id to neighbor id, until opened; residents who opened one.
_sessions: dict[str, str] = {}
_links: dict[str, str] = {}
_used_links: set[str] = set()
_joined: set[str] = set()


class UnknownResident(Exception):
    pass


class NotNeedsRescue(Exception):
    """Video is for residents in the rescue queue only."""


class NoVideo(Exception):
    """Nobody asked this resident for video yet."""


class UnknownLink(Exception):
    pass


class LinkUsed(Exception):
    """The link was opened already: it works once."""


def request(neighbor_id: str) -> RescueVideoLink:
    """A single-use link for the resident's camera, texted to their registry phone when SMS works."""
    resident = state.get(neighbor_id)
    if resident is None:
        raise UnknownResident(neighbor_id)
    if resident.status != TriageStatus.NEEDS_RESCUE:
        raise NotNeedsRescue(neighbor_id)
    if not vonage.video_configured():
        raise vonage.VonageUnavailable("VONAGE_APPLICATION_ID and VONAGE_PRIVATE_KEY are not set")
    if neighbor_id not in _sessions:
        _sessions[neighbor_id] = vonage.create_session()
    link_id = secrets.token_urlsafe(12)
    _links[link_id] = neighbor_id
    link = f"{settings.public_url}/v/{link_id}"
    return RescueVideoLink(neighbor_id=neighbor_id, link=link, sms_sent=_text(resident.phone, link))


def _text(phone: str, link: str) -> bool:
    """Text the link; the coordinator still has it on the dashboard when SMS is off or fails."""
    if not vonage.sms_configured():
        return False
    try:
        vonage.send_sms(phone, t("sms.videoLink", settings.resident_locale, link=link))
    except vonage.VonageUnavailable:
        logger.exception("the video link SMS failed")  # never log the number
        return False
    return True


def join(link_id: str) -> VideoAccess:
    """The resident's camera: a publisher token, once per link, and Spanish captions for the coordinator.

    A Vonage failure leaves the link unused. Captions that fail to start never block the video.
    """
    if link_id in _used_links:
        raise LinkUsed(link_id)
    neighbor_id = _links.get(link_id)
    if neighbor_id is None:
        raise UnknownLink(link_id)
    session_id = _sessions[neighbor_id]
    token = vonage.client_token(session_id, "publisher", PUBLISHER_TTL_S)
    del _links[link_id]
    _used_links.add(link_id)
    _joined.add(neighbor_id)
    try:
        vonage.start_captions(session_id, CAPTIONS_LANGUAGE)
    except vonage.VonageUnavailable:
        logger.exception("captions did not start for %s", neighbor_id)
    return VideoAccess(application_id=settings.vonage_application_id, session_id=session_id, token=token)


def watch(neighbor_id: str) -> RescueVideo:
    """What the coordinator's dashboard needs: waiting for the resident, or a token to watch them."""
    session_id = _sessions.get(neighbor_id)
    if session_id is None:
        raise NoVideo(neighbor_id)
    if neighbor_id not in _joined:
        return RescueVideo(neighbor_id=neighbor_id, joined=False)
    token = vonage.client_token(session_id, "subscriber", SUBSCRIBER_TTL_S)
    access = VideoAccess(application_id=settings.vonage_application_id, session_id=session_id, token=token)
    return RescueVideo(neighbor_id=neighbor_id, joined=True, access=access)


def forget() -> None:
    """Drop every session and link, so a reset demo starts clean."""
    _sessions.clear()
    _links.clear()
    _used_links.clear()
    _joined.clear()
