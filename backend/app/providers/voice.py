"""SLNG voice agents: the resident agent's outbound calls and browser sessions (#8).

A phone call needs an outbound SIP trunk attached to the agent in SLNG's dashboard, because SLNG
supplies no numbers (docs/findings/2026-09-19-slng-bring-your-own-number.md). Until one exists,
HACKFIRE_PHONE_CALLS stays off and the dashboard talks to the agent in the browser instead.
Web sessions ran against the live API on 2026-09-19. Dispatching a call and reading its state are
not yet run, for want of a trunk: the field names follow the API reference.
See https://docs.slng.ai/api-reference/calls/dispatch-call.md
"""

import httpx

from ..config import settings
from ..models import WebSession

_AGENTS_URL = "https://api.agents.slng.ai/v1/agents"
TIMEOUT_SECONDS = 15
_ENDED = {"completed", "failed"}


class VoiceUnavailable(Exception):
    """SLNG refused the request, did not answer, or answered in a shape we do not know."""


def phone_calls_configured() -> bool:
    return settings.phone_calls and web_sessions_configured()


def web_sessions_configured() -> bool:
    return bool(settings.slng_api_key and settings.slng_resident_agent_id)


def _request(method: str, path: str, body: dict | None = None) -> dict:
    try:
        response = httpx.request(
            method,
            f"{_AGENTS_URL}/{settings.slng_resident_agent_id}{path}",
            headers={"Authorization": f"Bearer {settings.slng_api_key}"},
            json=body,
            timeout=TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        answer = response.json()
    except (httpx.HTTPError, ValueError) as error:
        raise VoiceUnavailable(str(error)) from error
    if not isinstance(answer, dict):
        raise VoiceUnavailable(f"unexpected answer to {method} {path}")
    return answer


def call_resident(phone: str, arguments: dict[str, str]) -> str:
    """Dial one resident. Returns SLNG's call id. `arguments` fill the agent's call variables."""
    call = _request("POST", "/calls", {"phone_number": phone, "arguments": arguments})
    call_id = call.get("call_id") or call.get("id")
    if not call_id:
        raise VoiceUnavailable("the dispatch answer carries no call id")
    return str(call_id)


def call_ended(call_id: str) -> bool:
    """Whether the call is over, answered or not."""
    call = _request("GET", f"/calls/{call_id}")
    return call.get("call_ended_at") is not None or call.get("status") in _ENDED


def web_session(arguments: dict[str, str], participant_name: str) -> WebSession:
    """A browser conversation with the agent. `arguments` fill its call variables."""
    session = _request("POST", "/web-sessions", {"arguments": arguments, "participant_name": participant_name})
    try:
        return WebSession.model_validate(session)
    except ValueError as error:
        raise VoiceUnavailable("the web-session answer is missing fields") from error
