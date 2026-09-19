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


def coordinator_configured() -> bool:
    return bool(settings.slng_api_key and settings.slng_coordinator_agent_id)


def _request(method: str, agent_id: str, path: str = "", body: dict | None = None) -> dict:
    try:
        response = httpx.request(
            method,
            f"{_AGENTS_URL}/{agent_id}{path}",
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
    call = _request("POST", settings.slng_resident_agent_id, "/calls", {"phone_number": phone, "arguments": arguments})
    call_id = call.get("call_id") or call.get("id")
    if not call_id:
        raise VoiceUnavailable("the dispatch answer carries no call id")
    return str(call_id)


def call_ended(call_id: str) -> bool:
    """Whether the call is over, answered or not."""
    call = _request("GET", settings.slng_resident_agent_id, f"/calls/{call_id}")
    return call.get("call_ended_at") is not None or call.get("status") in _ENDED


def web_session(arguments: dict[str, str], participant_name: str) -> WebSession:
    """A browser conversation with the resident agent. `arguments` fill its call variables."""
    return _web_session({"arguments": arguments, "participant_name": participant_name}, settings.slng_resident_agent_id)


def coordinator_web_session() -> WebSession:
    """A browser conversation with the coordinator agent, which needs no call variables."""
    return _web_session({"participant_name": "Coordinator"}, settings.slng_coordinator_agent_id)


def _web_session(body: dict, agent_id: str) -> WebSession:
    session = _request("POST", agent_id, "/web-sessions", body)
    try:
        return WebSession.model_validate(session)
    except ValueError as error:
        raise VoiceUnavailable("the web-session answer is missing fields") from error


# SLNG's built-in end_call; its goodbye is English ("Thanks for calling. Goodbye!") unless set.
_END_CALL_TOOL_ID = "952eb6b1-fa3f-47a5-9ec5-ccee65d5eba3"
# Fields a GET returns that a PUT refuses.
_READ_ONLY = {
    "id", "created_at", "updated_at", "deleted_at", "organisation_id", "livekit_deployment",
    "models_validation_error", "tools", "template_variables",
}


def set_goodbye(agent_id: str, goodbye: str) -> None:
    """Make the agent's end_call say `goodbye`, changing nothing else.

    unmute 0.5.5 cannot set end_call's goodbye_message, and a PATCH cannot change tool attachments,
    so this reads the whole agent and PUTs it back. Raises VoiceUnavailable if SLNG refuses, or if
    the agent has no end_call attached.
    """
    agent = _request("GET", agent_id)
    body = {key: value for key, value in agent.items() if key not in _READ_ONLY}
    # A GET returns the call variables as template_variables; a PUT takes defaults plus options.
    variables = agent.get("template_variables") or {}
    if variables:
        body["template_defaults"] = {name: v["default"] for name, v in variables.items() if "default" in v}
        body["template_variable_options"] = {name: {"required": v.get("required", True)} for name, v in variables.items()}
    end_calls = [ref for ref in body.get("tool_refs", []) if ref.get("tool_id") == _END_CALL_TOOL_ID]
    if not end_calls:
        raise VoiceUnavailable(f"agent {agent_id} has no end_call attached")
    for ref in end_calls:
        ref["config_overrides"] = {
            **(ref.get("config_overrides") or {}),
            "type": "end_call",
            "goodbye_message": {"segments": [{"type": "literal", "value": goodbye}]},
        }
    _request("PUT", agent_id, body=body)
