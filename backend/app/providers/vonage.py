"""Vonage: live video from a resident who needs rescue, with captions, and the SMS with the link (#18).

The unified Vonage platform authenticates with an application id and its private key; one
application with the Video capability covers video, captions and the Messages API's SMS.

Checked against the docs and the installed SDK (vonage 4.9, vonage-video 1.6) on 2026-09-19:
routed sessions, client tokens (the SDK returns bytes), and the captions endpoint. The SDK's
captions model has no `es-ES` although the API supports it, so captions are started with the same
raw call the SDK makes. Not yet run against the live API: nobody has Vonage credentials yet. A
trial account only texts numbers added to its test list in the Vonage dashboard.
See https://developer.vonage.com/en/video/guides/live-caption
"""

import time
from functools import cache

from requests.exceptions import RequestException
from vonage import Auth, Vonage
from vonage_http_client.errors import HttpRequestError, VonageError
from vonage_messages import Sms
from vonage_video import SessionOptions, TokenOptions

from ..config import settings


class VonageUnavailable(Exception):
    """Vonage is not configured, refused the request, or did not answer."""


def video_configured() -> bool:
    return bool(settings.vonage_application_id and settings.vonage_private_key)


def sms_configured() -> bool:
    return video_configured() and bool(settings.vonage_sms_from)


@cache
def _client() -> Vonage:
    return Vonage(Auth(application_id=settings.vonage_application_id, private_key=settings.vonage_private_key))


def _guarded(call):
    if not video_configured():
        raise VonageUnavailable("VONAGE_APPLICATION_ID and VONAGE_PRIVATE_KEY are not set")
    try:
        return call()
    except (VonageError, RequestException, ValueError) as error:
        raise VonageUnavailable(str(error)) from error


def create_session() -> str:
    """A routed session: captions only work when Vonage's media router carries the audio."""
    video = _client().video
    # vonage-http-client leaves "Content-Type: application/json" on its shared headers after any JSON
    # request (captions, SMS), so the form-encoded session/create that follows got HTTP 415.
    video.http_client._headers.pop("Content-Type", None)
    return _guarded(lambda: video.create_session(SessionOptions(media_mode="routed")).session_id)


def client_token(session_id: str, role: str, ttl_s: int) -> str:
    """A browser token for the session: `publisher`, `subscriber` or `moderator`."""
    options = TokenOptions(session_id=session_id, role=role, exp=int(time.time()) + ttl_s)
    token = _guarded(lambda: _client().video.generate_client_token(options))
    return token.decode() if isinstance(token, bytes) else token


def start_captions(session_id: str, language: str) -> None:
    """Live captions for everyone who publishes with captions on. Already running is fine."""
    token = client_token(session_id, "moderator", 3600)
    http = _client().video.http_client
    body = {"sessionId": session_id, "token": token, "languageCode": language, "partialCaptions": True}

    def start() -> None:
        try:
            http.post(http.video_host, f"/v2/project/{settings.vonage_application_id}/captions", body)
        except HttpRequestError as error:
            if error.response.status_code != 409:  # 409: captions already on for this session
                raise

    _guarded(start)


def send_sms(to_e164: str, text: str) -> None:
    """One SMS through the Messages API. Numbers go without the plus sign."""
    message = Sms(to=to_e164.lstrip("+"), from_=settings.vonage_sms_from, text=text)
    _guarded(lambda: _client().messages.send(message))
