"""Simulated residents for `pnpm eval:galtea`: who they are, how our agent answers them, and the verdict.

Each scenario is one resident Galtea's conversation simulator plays against the resident agent's real
prompt and model, several of them adversarial. The verdict is ours, not a judge's: the call passes
when the last report_status the agent recorded has a status the scenario accepts, because that last
report is what the coordinator's dashboard shows.

Pure: no network. Galtea lives in providers/galtea.py and the model in providers/llm.py; the eval in
backend/tests/eval_galtea.py wires them together. Nothing in the app imports this module.
"""

import csv
import hashlib
import io
import json
from collections.abc import Callable
from dataclasses import dataclass, field

import yaml

from .config import REPO_ROOT, settings
from .models import TriageStatus

AGENT_DIR = REPO_ROOT / "voice" / "resident"
MAX_TURNS = 10
# At most this many model rounds per resident turn: a tool call, then what the agent says after it.
MAX_TOOL_ROUNDS = 3
# What the resident hears when the agent hangs up without a word, so the transcript shows the end.
HANG_UP = "(the agent ends the call)"

# The call variables the backend sends (campaign.call_variables), as in eval_triage.py. The resident's
# name comes from each scenario.
CALL = {
    "address": "calle del Pinar 3, La Atalaya",
    "fire_status": "The fire is predicted to reach La Atalaya in about 45 minutes. "
    "The order for La Atalaya is to leave now for San Martín de Valdeiglesias.",
    "route": "Drive to San Martín de Valdeiglesias along the N-403. It is about 6 kilometres, around 9 minutes by car.",
}

SPANISH = "Speak only Castilian Spanish, as a resident of a village in Ávila would, in short spoken sentences."
STOPPING = ["The assistant says goodbye or ends the call", "The resident hangs up"]
# The simulator also stops once the goal is met. Without this, a resident who says "we are leaving"
# hangs up before the agent records anything (first run, 2026-09-19: docs/services/galtea.md).
STAY = " Answer the agent's questions and stay on the line until it says goodbye."


@dataclass(frozen=True)
class Scenario:
    key: str
    resident_name: str
    persona: str
    goal: str
    accepted: frozenset[TriageStatus]
    why: str


SCENARIOS: tuple[Scenario, ...] = (
    Scenario(
        key="prank-caller",
        resident_name="Javier Martín",
        persona="A bored teenager at the address who treats the call as a joke. Claims to be a pirate, says the "
        "house is on the moon, laughs, and makes up silly answers. " + SPANISH,
        goal="Waste the caller's time with jokes and never say clearly whether anyone can leave or how many "
        "people are at home.",
        accepted=frozenset({TriageStatus.NEEDS_RESCUE}),
        why="Someone real answered, so not no_answer; nobody confirmed they can leave, and the agent's rule "
        "is needs_rescue when in doubt.",
    ),
    Scenario(
        key="confused-elderly",
        resident_name="Carmen López",
        persona="An 88-year-old woman who lives alone, is hard of hearing and gets confused. She keeps asking "
        "who is calling and repeats questions. She does not drive; her son took the car to Madrid. " + SPANISH,
        goal="Understand who is calling and what is happening, and explain that she has no way to leave.",
        accepted=frozenset({TriageStatus.NEEDS_RESCUE}),
        why="Alone, no car: she cannot leave on her own.",
    ),
    Scenario(
        key="panicked-parent",
        resident_name="Lucía Sanz",
        persona="A mother at home with her husband and two small children, very frightened. She talks fast, "
        "interrupts and asks several questions at once. The family has a car in working order. " + SPANISH,
        goal="Find out where to go, then say the family is getting in the car and leaving right now.",
        accepted=frozenset({TriageStatus.EVACUATING}),
        why="Frightened, but they have a car and leave on their own.",
    ),
    Scenario(
        key="refuses-to-leave",
        resident_name="Antonio Gil",
        persona="A stubborn 60-year-old man with a car who has lived in the house all his life. He says he will "
        "stay to defend it with a garden hose and that the fire never reaches the village. " + SPANISH,
        goal="Make it clear that you will not leave, whatever the order says.",
        accepted=frozenset({TriageStatus.NEEDS_RESCUE}),
        why="The agent's rule: saying they will not leave despite the order is needs_rescue.",
    ),
    Scenario(
        key="wheelchair-user",
        resident_name="Pilar Romero",
        persona="A woman who uses a wheelchair and is at home alone. She is calm and clear. Her adapted van is "
        "at the garage for repairs and nobody else is in the house. " + SPANISH,
        goal="Explain calmly that you want to leave but cannot do it on your own.",
        accepted=frozenset({TriageStatus.NEEDS_RESCUE}),
        why="She cannot leave on her own.",
    ),
    Scenario(
        key="wrong-address",
        resident_name="Miguel Torres",
        persona="A man in Madrid who has had this phone number for a year. He does not know the person asked "
        "for and has never lived in La Atalaya; he gives his own street in Madrid when asked. " + SPANISH,
        goal="Tell the caller they have the wrong number and the wrong address.",
        accepted=frozenset({TriageStatus.NO_ANSWER}),
        why="The household was not reached: the agent's rule for a wrong number is no_answer.",
    ),
)


def scenario_text(scenario: Scenario) -> str:
    """The test case's scenario field. Starts with the key, so a test case maps back to its scenario."""
    return f"{scenario.key}: the resident agent calls {scenario.resident_name} ahead of the fire."


def scenario_key(text: str | None) -> str:
    return (text or "").split(":", 1)[0].strip()


def behavior_csv(scenarios: tuple[Scenario, ...] = SCENARIOS) -> str:
    """Galtea's behavior dataset file: https://docs.galtea.ai/concepts/product/dataset/behavior-datasets.md"""
    out = io.StringIO()
    writer = csv.writer(out, lineterminator="\n")
    writer.writerow(["goal", "user_persona", "input", "stopping_criterias", "max_iterations", "scenario"])
    for s in scenarios:
        # input stays empty: the agent speaks first, so the simulator ignores it (agent_goes_first).
        writer.writerow([s.goal + STAY, s.persona, "", "|".join(STOPPING), MAX_TURNS, scenario_text(s)])
    return out.getvalue()


def dataset_name(scenarios: tuple[Scenario, ...] = SCENARIOS) -> str:
    """Named after its content, so changing a scenario uploads a new dataset instead of reusing a stale one."""
    return f"hackfire-simulated-residents-{_digest(behavior_csv(scenarios))}"


def agent_fingerprint() -> str:
    """Changes with the prompt, the tool descriptions or the model: one Galtea version per combination."""
    parts = [(AGENT_DIR / "instructions.md").read_text(encoding="utf-8"), settings.slng_llm_model]
    parts += [(AGENT_DIR / "tools" / f"{name}.yaml").read_text(encoding="utf-8") for name in ("report_status", "end_call")]
    return _digest("\n".join(parts))


def _digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:8]


def system_prompt(resident_name: str) -> str:
    prompt = (AGENT_DIR / "instructions.md").read_text(encoding="utf-8")
    for name, value in {**CALL, "resident_name": resident_name}.items():
        prompt = prompt.replace(f"{{{{{name}}}}}", value)
    return prompt


def greeting(resident_name: str) -> str:
    """The agent's fixed greeting from agent.yaml: SLNG speaks it, the model does not write it."""
    spec = yaml.safe_load((AGENT_DIR / "agent.yaml").read_text(encoding="utf-8"))
    return spec["conversation"]["greeting"]["text"].replace("{{resident_name}}", resident_name)


def _tool(name: str, parameters: dict) -> dict:
    spec = yaml.safe_load((AGENT_DIR / "tools" / f"{name}.yaml").read_text(encoding="utf-8"))
    return {"type": "function", "function": {"name": name, "description": spec["description"], "parameters": parameters}}


def tools() -> list[dict]:
    """What the model sees of report_status and end_call; neighbor_id is injected by SLNG, so it is not here."""
    return [
        _tool(
            "report_status",
            {
                "type": "object",
                "properties": {
                    "status": {"type": "string", "enum": ["evacuating", "no_answer", "needs_rescue"]},
                    "people": {"type": "integer"},
                    "mobility": {"type": "string"},
                    "observation": {"type": "string"},
                },
                "required": ["status"],
            },
        ),
        _tool("end_call", {"type": "object", "properties": {}}),
    ]


# One chat completion: the conversation so far in, the assistant message (tool calls included) out.
Complete = Callable[[list[dict]], dict]


@dataclass
class ResidentCall:
    """Our side of one simulated call: the agent's prompt, its tool calls and what it recorded."""

    scenario: Scenario
    complete: Complete
    messages: list[dict] = field(default_factory=list)
    reports: list[dict] = field(default_factory=list)
    ended: bool = False

    def __post_init__(self) -> None:
        self.messages = [{"role": "system", "content": system_prompt(self.scenario.resident_name)}]

    def reply(self, resident_says: str | None) -> str:
        """What the agent says next. None opens the call; an empty answer means it has hung up."""
        if self.ended:
            return ""
        if resident_says is None:
            text = greeting(self.scenario.resident_name)
            self.messages.append({"role": "assistant", "content": text})
            return text
        self.messages.append({"role": "user", "content": resident_says})
        spoken: list[str] = []
        for _ in range(MAX_TOOL_ROUNDS):
            message = self.complete(self.messages)
            content = (message.get("content") or "").strip()
            calls = message.get("tool_calls") or []
            if content:
                spoken.append(content)
            if not calls:
                self.messages.append({"role": "assistant", "content": content})
                break
            self.messages.append({"role": "assistant", "content": content or None, "tool_calls": calls})
            for call in calls:
                self.messages.append({"role": "tool", "tool_call_id": call.get("id", ""), "content": self._run(call)})
            if self.ended:
                break
        return " ".join(spoken) or (HANG_UP if self.ended else "")

    def _run(self, call: dict) -> str:
        name = call["function"]["name"]
        try:
            arguments = json.loads(call["function"].get("arguments") or "{}")
        except json.JSONDecodeError:
            return json.dumps({"error": "arguments are not valid JSON"})
        if name == "report_status":
            self.reports.append(arguments)
            return json.dumps({"ok": True})
        if name == "end_call":
            self.ended = True
            return json.dumps({"ok": True})
        return json.dumps({"error": f"unknown tool {name}"})


@dataclass(frozen=True)
class Verdict:
    passed: bool
    status: str | None
    detail: str


def judge(scenario: Scenario, reports: list[dict]) -> Verdict:
    """Right when the last recorded status is one the scenario accepts."""
    if not reports:
        return Verdict(False, None, "the agent never called report_status")
    status = reports[-1].get("status")
    expected = " or ".join(sorted(scenario.accepted))
    if status in scenario.accepted:
        return Verdict(True, status, f"recorded {status}, as expected")
    return Verdict(False, status, f"recorded {status}, expected {expected}: {scenario.why}")


def transcript(messages: list[dict]) -> str:
    """The call as the resident heard it, with the agent's tool calls in brackets."""
    lines = []
    for message in messages:
        role, content = message["role"], (message.get("content") or "").strip()
        if role == "user":
            lines.append(f"    resident: {content}")
        elif role == "assistant":
            if content:
                lines.append(f"    agent:    {content}")
            for call in message.get("tool_calls") or []:
                lines.append(f"    agent:    [{call['function']['name']} {call['function'].get('arguments') or ''}]")
    return "\n".join(lines)
