"""The demo's last resort (#13): type what a resident said and triage it like a call would.

If the voice agent fails on stage, the presenter types the resident's answer ("my mother can't
walk") into the dashboard. The LLM classifies it with the voice agent's own rules, read from the
"Cómo clasificar" section of voice/resident/instructions.md, not a keyword list, and the result goes
through the same report_status path, so the pin, the rescue queue and the crew alert behave exactly
as after a real call.
"""

import json

import httpx
from pydantic import BaseModel, Field, ValidationError

from .config import REPO_ROOT, settings
from .models import ReportStatusRequest, TriageStatus
from .providers import llm

TIMEOUT_SECONDS = 20

AGENT_PROMPT = REPO_ROOT / "voice" / "resident" / "instructions.md"
RULES_HEADING = "# Cómo clasificar"

FALLBACK_RULES = """Decide:
- status: "needs_rescue" when they cannot leave on their own or it is not safe for them to try
  (no car, road blocked, someone cannot walk or depends on others, fire or smoke already around
  them, or they refuse to leave). "evacuating" when they can and will leave on their own, are
  already leaving or are already out, or are staying indoors under an order and are fine.
  "no_answer" only when nobody real answered (voicemail, silence, wrong number).
  If unsure between evacuating and needs_rescue, choose needs_rescue.
- people: how many people are at the home, counting the speaker, or null if not said.
- mobility: a few words, in English, on how they will leave or what stops them, or null.
- observation: a few words, in English, on what they see or report, or null.
Judge by meaning, not by single words."""


def _agent_rules() -> str:
    """The voice agent's classification rules, so a typed answer is judged exactly like a call."""
    if AGENT_PROMPT.exists():
        text = AGENT_PROMPT.read_text(encoding="utf-8")
        if RULES_HEADING in text:
            return text.split(RULES_HEADING, 1)[1].split("\n# ", 1)[0].strip()
    return FALLBACK_RULES


SYSTEM_PROMPT = f"""You triage residents during a wildfire evacuation for the emergency coordinator.
You get what one resident said, in any language, and fill in the fields of report_status.
These are the voice agent's rules for it:

{_agent_rules()}

Write mobility and observation as a few words in English. Never invent details that were not said."""


class Classification(BaseModel):
    status: TriageStatus = Field(description="evacuating, no_answer or needs_rescue")
    people: int | None = None
    mobility: str | None = None
    observation: str | None = None


class ClassifierUnavailable(Exception):
    """No LLM configured, or it failed: the dashboard falls back to the manual buttons."""


def available() -> bool:
    return bool(settings.nebius_api_key and settings.nebius_model)


def classify(text: str) -> Classification:
    if not available():
        raise ClassifierUnavailable("NEBIUS_API_KEY and NEBIUS_MODEL are not set")
    schema = Classification.model_json_schema()
    schema["properties"]["status"] = {"type": "string", "enum": ["evacuating", "no_answer", "needs_rescue"]}
    try:
        with httpx.Client(timeout=TIMEOUT_SECONDS) as client:
            content = llm.chat(
                client,
                [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": text}],
                temperature=0,
                response_format={
                    "type": "json_schema",
                    "json_schema": {"name": "triage", "schema": schema, "strict": True},
                },
            )
        return Classification.model_validate(json.loads(content))
    except (httpx.HTTPError, ValueError, ValidationError, KeyError) as error:
        raise ClassifierUnavailable(str(error)) from error


def report_from_text(neighbor_id: str, text: str) -> tuple[ReportStatusRequest, Classification]:
    result = classify(text)
    observation = result.observation or text.strip()[:200]
    report = ReportStatusRequest(
        neighbor_id=neighbor_id,
        status=result.status,
        people=result.people,
        mobility=result.mobility,
        observation=observation,
    )
    return report, result
