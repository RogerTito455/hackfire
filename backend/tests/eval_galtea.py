"""Simulated residents, some adversarial, call-test the resident agent through Galtea.

Galtea's conversation simulator plays each resident in app/simulated_residents.py; the agent answers
with its real prompt (voice/resident/instructions.md), its real tool descriptions and the model it
thinks with, through SLNG's Context Router. A scenario passes when the agent's last report_status has
the status that scenario expects. Every conversation also lands in Galtea as a session of the version
named after the agent's fingerprint, for reading and for Galtea's own metrics.

Not part of `pnpm check`: it calls Galtea and SLNG, spends Galtea credits, and a model's answer can
vary. Run it with `pnpm eval:galtea`, or one scenario with `pnpm eval:galtea -k prank-caller`.
See docs/services/galtea.md.
"""

import httpx
import pytest

from app import simulated_residents as sim
from app.config import settings
from app.providers import galtea, llm

pytestmark = [
    pytest.mark.skipif(not galtea.configured(), reason="needs GALTEA_API_KEY (docs/services/galtea.md)"),
    pytest.mark.skipif(not llm.configured(), reason="needs SLNG_API_KEY"),
]

PRODUCT = "HackFire resident agent"
PRODUCT_FIELDS = {
    "description": "An outbound voice agent that calls registered residents of a zone a wildfire is heading "
    "for, on behalf of the emergency coordination. It gives the coordinator's order and the exit route, "
    "asks whether they can leave on their own, how many are at home and what they see, and records the "
    "outcome (evacuating, needs_rescue or no_answer) for the coordinator's dashboard. It speaks Castilian Spanish.",
    "capabilities": "Gives the evacuation order and route from the call data. Asks three short questions. "
    "Records the triage status with report_status. Ends the call with end_call.",
    "inabilities": "Cannot send help itself, promise a rescue time, give medical advice or say anything about "
    "the fire beyond the call data. It is not 112.",
    "policies": "Never claims to be 112 or an official emergency service. Never invents a route. When in doubt "
    "between evacuating and needs_rescue, records needs_rescue. Records no_answer only when the household was "
    "not reached. Tells anyone in immediate danger to hang up and call 112.",
    "interactionMode": "CONVERSATIONAL",
    "primaryTask": "CONVERSATIONAL_ASSISTANCE",
}


@pytest.fixture(scope="module")
def run() -> dict:
    """The Galtea product, version and test cases, created on first use and reused after."""
    try:
        client = galtea.connect()
        product_id = galtea.ensure_product(client, PRODUCT, **PRODUCT_FIELDS)
        version_id = galtea.ensure_version(
            client,
            product_id,
            f"resident-{sim.agent_fingerprint()}",
            description=f"voice/resident prompt and tools, model {settings.slng_llm_model}",
            system_prompt=(sim.AGENT_DIR / "instructions.md").read_text(encoding="utf-8"),
        )
        cases = galtea.ensure_behavior_dataset(
            client, product_id, sim.dataset_name(), sim.behavior_csv(), expected=len(sim.SCENARIOS), language="es"
        )
    except galtea.GalteaUnavailable as error:
        pytest.exit(str(error), returncode=2)
    except Exception as error:  # the SDK's own errors: a bad key, Galtea down
        pytest.exit(f"Galtea setup failed: {type(error).__name__}: {error}", returncode=2)
    by_key = {sim.scenario_key(case.scenario): case.id for case in cases}
    print(f"\nGaltea product {product_id}, version {version_id}: {galtea.PLATFORM_URL}")
    return {"client": client, "version_id": version_id, "cases": by_key}


@pytest.fixture(scope="module")
def slng():
    with httpx.Client(timeout=60) as client:
        yield client


@pytest.mark.parametrize("scenario", sim.SCENARIOS, ids=lambda s: s.key)
def test_simulated_resident_is_triaged_right(scenario: sim.Scenario, run: dict, slng: httpx.Client) -> None:
    test_case_id = run["cases"].get(scenario.key)
    assert test_case_id, f"no Galtea test case for {scenario.key}; the dataset is {sim.dataset_name()}"

    def complete(messages: list[dict]) -> dict:
        return llm.complete(slng, messages, agent_id="hackfire-eval-galtea", tools=sim.tools(), temperature=0.2)

    call = sim.ResidentCall(scenario, complete)
    simulation = galtea.simulate(run["client"], run["version_id"], test_case_id, call.reply, max_turns=sim.MAX_TURNS)
    verdict = sim.judge(scenario, call.reports)

    print(f"\n--- {scenario.key}: {'PASS' if verdict.passed else 'FAIL'}, {verdict.detail}")
    print(f"    session {simulation.session_id}, {simulation.turns} turns, stopped: {simulation.stopping_reason}")
    print(sim.transcript(call.messages))
    assert verdict.passed, verdict.detail
