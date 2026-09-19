"""SMS through Twilio's REST API, for the crew alert on every new rescue (#9).

SLNG's own "Send SMS" is a tool its agents call, not an API our backend can call, and it runs on
Twilio anyway (docs/services/slng.md), so the backend talks to Twilio directly. Nothing is sent
unless TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_FROM_NUMBER and HACKFIRE_CREW_PHONE are set.
Not yet run against the live API: nobody has Twilio credentials yet.
"""

import httpx

from ..config import settings

_MESSAGES = "https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json"
TIMEOUT_SECONDS = 10


def configured() -> bool:
    return all((settings.twilio_account_sid, settings.twilio_auth_token, settings.twilio_from_number))


def send(to: str, body: str) -> str:
    """Send one SMS and return Twilio's message id. Raises httpx.HTTPError on failure."""
    response = httpx.post(
        _MESSAGES.format(sid=settings.twilio_account_sid),
        auth=(settings.twilio_account_sid, settings.twilio_auth_token),
        data={"To": to, "From": settings.twilio_from_number, "Body": body},
        timeout=TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    return response.json()["sid"]
