"""The crews' room: the command post shares its map and panels, and its voice, with the fire crews.

One routed Vonage session for the whole operation. The coordinator publishes their screen (the
dashboard) with their microphone; each crew opens the room's link on a phone, sees the map live and
can talk back. Captions in Spanish, so a crew in a noisy truck can read what was said. The link is
texted to the crew phone when SMS works. In memory; a demo reset closes the room.
"""

import logging
import secrets

from .config import settings
from .i18n import t
from .models import CrewRoom, VideoAccess
from .providers import vonage

logger = logging.getLogger(__name__)

CAPTIONS_LANGUAGE = "es-ES"
TOKEN_TTL_S = 4 * 60 * 60

# The link the crews are given. Every deploy empties this process, so the id comes from the
# environment when it is set: the same link then reaches the room again, with a new Vonage session
# behind it. Unset, it is random per process and a deploy costs the crews their link.
ROOM_ID = settings.crew_room or secrets.token_urlsafe(9)
_session: str | None = None
# A demo reset closes the room on purpose; losing the process does not. A fresh process starts
# open, so a crew that taps the link it was texted gets in after a deploy.
_closed = False


class UnknownRoom(Exception):
    pass


def open_room() -> CrewRoom:
    """Open the room and return its link, with the command post's own publisher token."""
    global _closed
    _closed = False
    opened = _open_session()
    if opened:
        _text_the_crew(_link())
    return CrewRoom(link=_link(), access=_access("publisher"))


def join(room_id: str) -> VideoAccess:
    """A crew's way in: it watches the command post and can talk back.

    The room is opened here too when the process has no session: a crew that taps the link it was
    texted gets in after a deploy, whether or not the command post has re-shared. A demo reset,
    which closes the room on purpose, is different: then the link is unknown again.
    """
    if room_id != ROOM_ID or _closed:
        raise UnknownRoom(room_id)
    _open_session()
    return _access("publisher")


def forget() -> None:
    """A demo reset: the room closes until the command post shares again."""
    global _session, _closed
    _session, _closed = None, True


def _open_session() -> bool:
    """The room's Vonage session, made once per process. True when this call made it."""
    global _session
    if not vonage.video_configured():
        raise vonage.VonageUnavailable("VONAGE_APPLICATION_ID and VONAGE_PRIVATE_KEY are not set")
    if _session is not None:
        return False
    _session = vonage.create_session()
    try:
        vonage.start_captions(_session, CAPTIONS_LANGUAGE)
    except vonage.VonageUnavailable:
        logger.exception("captions did not start in the crews' room")
    return True


def _link() -> str:
    return f"{settings.public_url}/crew/{ROOM_ID}"


def _access(role: str) -> VideoAccess:
    token = vonage.client_token(_session, role, TOKEN_TTL_S)
    return VideoAccess(application_id=settings.vonage_application_id, session_id=_session, token=token)


def _text_the_crew(link: str) -> None:
    if not (settings.crew_phone and vonage.sms_configured()):
        return
    try:
        vonage.send_sms(settings.crew_phone, t("sms.crewRoom", settings.crew_locale, link=link))
    except vonage.VonageUnavailable:
        logger.exception("the crews' room SMS failed")  # never log the number
