"""The crews' room: the command post shares its map and panels, and its voice, with the fire crews.

One routed Vonage session for the whole operation. The coordinator publishes their screen (the
dashboard) with their microphone; each crew opens the room's link on a phone, sees the map live and
can talk back. Captions in Spanish, so a crew in a noisy truck can read what was said. The link is
texted to the crew phone when SMS works. In memory; a demo reset closes the room.
"""

import logging
import secrets

from .config import settings
from .models import CrewRoom, VideoAccess
from .providers import vonage

logger = logging.getLogger(__name__)

CAPTIONS_LANGUAGE = "es-ES"
TOKEN_TTL_S = 4 * 60 * 60

_room: dict[str, str] = {}  # "id" and "session" once the room is open


class UnknownRoom(Exception):
    pass


def open_room() -> CrewRoom:
    """Open the room (once) and return its link, with the command post's own publisher token."""
    if not vonage.video_configured():
        raise vonage.VonageUnavailable("VONAGE_APPLICATION_ID and VONAGE_PRIVATE_KEY are not set")
    if not _room:
        session_id = vonage.create_session()
        _room.update(id=secrets.token_urlsafe(9), session=session_id)
        try:
            vonage.start_captions(session_id, CAPTIONS_LANGUAGE)
        except vonage.VonageUnavailable:
            logger.exception("captions did not start in the crews' room")
        _text_the_crew(_link())
    return CrewRoom(link=_link(), access=_access("publisher"))


def join(room_id: str) -> VideoAccess:
    """A crew's way in: it watches the command post and can talk back."""
    if not _room or room_id != _room["id"]:
        raise UnknownRoom(room_id)
    return _access("publisher")


def forget() -> None:
    _room.clear()


def _link() -> str:
    return f"{settings.public_url}/crew/{_room['id']}"


def _access(role: str) -> VideoAccess:
    token = vonage.client_token(_room["session"], role, TOKEN_TTL_S)
    return VideoAccess(application_id=settings.vonage_application_id, session_id=_room["session"], token=token)


def _text_the_crew(link: str) -> None:
    if not (settings.crew_phone and vonage.sms_configured()):
        return
    try:
        vonage.send_sms(settings.crew_phone, f"HackFire: la coordinación comparte el mapa con los equipos. Entre aquí: {link}")
    except vonage.VonageUnavailable:
        logger.exception("the crews' room SMS failed")  # never log the number
