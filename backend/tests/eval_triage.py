"""How the resident agent's model classifies what a resident says, without voice.

The real prompt (voice/resident/instructions.md) and the real report_status description go to the
model the agent thinks with, through SLNG's Context Router; each case is a call that has reached the
three questions, and the model must record the right triage status. Not part of `pnpm check`: it
calls SLNG, and a model's answer can vary.
Run it with `pnpm eval:triage` after changing the prompt, the tool description or the model.
"""

import json

import httpx
import pytest
import yaml

from app.config import REPO_ROOT
from app.providers import llm

AGENT_DIR = REPO_ROOT / "voice" / "resident"

pytestmark = pytest.mark.skipif(not llm.configured(), reason="needs SLNG_API_KEY")


def _system_prompt() -> str:
    prompt = (AGENT_DIR / "instructions.md").read_text(encoding="utf-8")
    return prompt.replace("{{resident_name}}", "Carmen López").replace("{{address}}", "calle del Pinar 3, La Atalaya")


def _tool(name: str, parameters: dict) -> dict:
    spec = yaml.safe_load((AGENT_DIR / "tools" / f"{name}.yaml").read_text(encoding="utf-8"))
    return {"type": "function", "function": {"name": name, "description": spec["description"], "parameters": parameters}}


# What the model sees of the SLNG tools: neighbor_id is injected by the agent, so it is not here.
TOOLS = [
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


def _call_up_to_the_answer(answer: str) -> list[dict]:
    return [
        {"role": "system", "content": _system_prompt()},
        {"role": "assistant", "content": "Hola, buenas. ¿Hablo con Carmen López?"},
        {"role": "user", "content": "Sí, soy yo."},
        {
            "role": "assistant",
            "content": (
                "Le llama un asistente automático de la coordinación de la emergencia, por el incendio que se "
                "acerca a su zona. Se espera que el fuego llegue a La Atalaya en unos cuarenta y cinco minutos, "
                "y la orden es salir. Su ruta es en coche hacia Cebreros, unos trece kilómetros. "
                "¿Pueden salir por su cuenta?"
            ),
        },
        {"role": "user", "content": answer},
        {"role": "assistant", "content": "¿Cuántas personas hay en la casa?"},
        {"role": "user", "content": "Dos, mi madre y yo."},
        {"role": "assistant", "content": "¿Qué ven desde donde están?"},
        {"role": "user", "content": "Humo hacia el norte, detrás del pinar."},
    ]


@pytest.mark.parametrize(
    ("answer", "expected"),
    [
        ("No tenemos coche y por aquí no pasa ningún autobús.", "needs_rescue"),
        ("No podemos, nos han dicho que la carretera está cortada.", "needs_rescue"),
        ("Yo sí podría, pero mi madre no puede andar.", "needs_rescue"),
        ("Sí, cogemos el coche y salimos ahora mismo.", "evacuating"),
    ],
)
def test_the_model_classifies_the_answer(answer: str, expected: str) -> None:
    with httpx.Client(timeout=60) as client:
        message = llm.complete(
            client, _call_up_to_the_answer(answer), agent_id="hackfire-eval-triage", tools=TOOLS, temperature=0
        )

    calls = [c["function"] for c in message.get("tool_calls") or []]
    reports = [json.loads(c["arguments"]) for c in calls if c["name"] == "report_status"]
    assert reports, f"no report_status call; the model said: {message.get('content')!r}"
    assert reports[0]["status"] == expected, reports[0]
