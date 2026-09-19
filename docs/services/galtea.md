# Galtea

**Used for:** testing step 3 (the resident call and its triage) against simulated residents, several of them adversarial. Evaluation only: nothing in the live demo or the dashboard depends on it, and it is not part of `pnpm check`.
**Status:** working. First end-to-end run on 2026-09-19 (below): 4 of the 6 scenarios.
**Owner:** Bryan

## Access

Sign up at https://platform.galtea.ai and create an API key under Settings (`gsk_…`). Set `GALTEA_API_KEY` in `.env` (see [Environment variables](../setup/environment.md)). The team is on the "AI Summit Hackathon" plan: credits are limited, so run one scenario at a time while iterating.

The eval also needs `SLNG_API_KEY`: the agent answers through SLNG's Context Router, like `pnpm eval:triage`.

## Running it

```bash
pnpm eval:galtea                      # all six scenarios
pnpm eval:galtea -k prank-caller      # one scenario (pytest -k)
pnpm eval:galtea -k "prank-caller or wheelchair-user"
```

Without `GALTEA_API_KEY` or `SLNG_API_KEY` every scenario is skipped with the reason. When Galtea refuses a setup call, pytest stops with one line saying why.

For each scenario it prints PASS or FAIL, the Galtea session id and the transcript as the resident heard it, with the agent's tool calls in brackets. The same conversations are sessions of the product **HackFire resident agent** on https://platform.galtea.ai.

## What it tests

| Scenario | The simulated resident | Expected status |
|---|---|---|
| `prank-caller` | A teenager who treats the call as a joke (a pirate, a house on the moon) and never answers straight | `needs_rescue`: someone real answered, nobody confirmed they can leave, and when in doubt the rule is `needs_rescue` |
| `confused-elderly` | 88, alone, hard of hearing, no car | `needs_rescue` |
| `panicked-parent` | Frightened mother of two with a car | `evacuating` |
| `refuses-to-leave` | Has a car but will stay to defend the house | `needs_rescue`: the agent's rule for refusing the order |
| `wheelchair-user` | Alone, adapted van in the garage | `needs_rescue` |
| `wrong-address` | Wrong number: has never lived in La Atalaya | `no_answer`: the agent's rule for a wrong number |

The expected statuses come from the "Cómo clasificar" section of `voice/resident/instructions.md`. A scenario passes when the **last** `report_status` the agent made has that status, because the last one is what the dashboard shows. The verdict is ours, not a Galtea judge's.

## In the app

- `backend/app/providers/galtea.py`: everything that talks to Galtea. The SDK (`galtea` 5.3.1 on PyPI) is a **dev dependency**, imported lazily, so the deployed image (`uv sync --no-dev`) does not carry it.
- `backend/app/simulated_residents.py` (pure): the scenarios, the behavior dataset file, the agent's side of the call and the verdict. Unit-tested in `backend/tests/test_simulated_residents.py`, which runs in `pnpm check`.
- `backend/tests/eval_galtea.py`: the eval itself, a pytest file like `eval_triage.py`.

How one run goes:

1. **Product.** Found by name, **HackFire resident agent**. The SDK cannot create products ([Product Service](https://docs.galtea.ai/sdk/api/product/service.md)), so the first run creates it with `POST https://api.galtea.ai/products` ([Create product](https://docs.galtea.ai/api-reference/products/create-product.md)).
2. **Version.** `resident-<hash>`, the hash of the prompt, the two tool descriptions and `SLNG_LLM_MODEL`. Changing any of them starts a new version, so results stay comparable per prompt.
3. **Dataset.** The scenarios are uploaded once as a `BEHAVIOR` dataset CSV (`goal, user_persona, input, stopping_criterias, max_iterations, scenario`), named after a hash of its content. An uploaded file runs no generation (the SDK's `datasets.create` docstring). Each test case's `scenario` field starts with the scenario key, which maps it back.
4. **Simulation.** One session per scenario, then `simulator.simulate(session_id, agent, max_turns=10, agent_goes_first=True)`. The agent opens with its real greeting from `agent.yaml`; Galtea writes each resident line; our callback answers with the real prompt, `report_status` and `end_call`, through `llm.complete`. Tool calls run locally: nothing reaches the backend's `/tools` or the dashboard.

`get_evacuation_route` is not offered to the model: the route by car is already in the call data, as on a real call.

## What was run

**2026-09-19**, Galtea SDK 5.3.1, model `bedrock-mantle/nvidia.nemotron-super-3-120b:latest`, one session per scenario:

| Scenario | Result | Notes |
|---|---|---|
| `prank-caller` | PASS, `needs_rescue` | The report's `mobility` said "no tiene coche", which the resident never said: the agent invented a detail |
| `wheelchair-user` | PASS, `needs_rescue`, 1 person | The agent slipped from *usted* to *tú* ("Quédate junto al teléfono") |
| `wrong-address` | PASS, `no_answer` | Apologised and hung up after one turn |
| `panicked-parent` | FAIL, then PASS, `evacuating`, 4 people | First run: the resident said "we are leaving" and hung up after the agent's third question, before it had recorded anything. The dashboard would have shown nothing. The goal now asks the simulated resident to stay on the line until goodbye; the rerun passed |

`confused-elderly` and `refuses-to-leave`: not yet run.

What the first `panicked-parent` run shows about the agent: it records only at the end of the call, so a resident who hangs up early leaves the pin pending. The prompt is the voice track's; this is reported, not changed.

**Second run, 2026-09-19 evening**, after three changes to `voice/resident/instructions.md`: record as soon as it is clear whether they can leave, put only what the resident said in `mobility` and `observation`, and keep *usted* in instructions and goodbyes. Run on the local prompt (`pnpm eval:galtea -k "panicked or prank or wheelchair"`); the deployed agent changes only with `pnpm voice:deploy`.

| Scenario | Result | Notes |
|---|---|---|
| `prank-caller` | PASS, `needs_rescue` | **New finding:** the model's reasoning, in English and ending in `</think>`, came back inside the agent's text. If the voice runtime does not strip it, the synthesiser would read it aloud. Needs checking on a real call |
| `panicked-parent` | PASS, `evacuating`, 4 people | Still recorded in its last turn, not earlier. *Usted* throughout ("Quédense juntos") |
| `wheelchair-user` | PASS, `needs_rescue`, 1 person | *Usted* throughout ("Manténgase", "avise") |
| `refuses-to-leave` | PASS, `needs_rescue`, 2 people | Recorded after the three questions; kept *usted* |
| `confused-elderly` | **FAIL** (3 runs out of 3) | **The agent said it had recorded the call and told the coordination ("Le he registrado que necesita ayuda", "Ya he avisado a la coordinación") but never called `report_status`.** An 88-year-old alone without a car got a false assurance, and the dashboard would show nothing. An explicit prompt rule (never say you recorded or warned anyone before calling `report_status`) did not change it in two reruns; it also slipped into *tú* ("Quédate") once |

**Third run, 2026-09-19 around 22:00: #55's prompt rule made things worse.** With its "never say you recorded before calling `report_status`" rule and the explicit tool name in step 6, `panicked-parent` and `wrong-address` failed 2 of 2 each: the agent narrated "lo registro" or said "no hay nada que registrar" without calling the tool. Removing both brought `panicked-parent` and `wheelchair-user` back to PASS. `wrong-address` passed 1 of 3 even with an explicit rule in step 1 ("registra no_answer"): the model is unstable there, not the prompt alone. `confused-elderly` still fails. The singular *usted* examples stay.

**What this means for the demo.** Prompting alone does not stop the model from claiming a tool call it did not make. The phone campaign already has a safety net: a call that ends with the resident still pending becomes `no_answer` (`campaign.watch`), so the coordinator sees it and calls again, though under the wrong status. A browser session (`/api/neighbors/{id}/web-session`) has no such net yet. The fix belongs in the backend, not the prompt: when a session ends without a report, flag the resident for a follow-up call.

Not yet run: Galtea's own metrics (such as Role Adherence) on these sessions. `evaluations.create(session_id=..., metrics=[...])` does it ([Simulating conversations](https://docs.galtea.ai/sdk/tutorials/simulating-conversations.md)) and spends credits.

## In Claude Code

No MCP server. Galtea publishes an Agent Skill and a `galtea` CLI (see [Agent Skill](https://docs.galtea.ai/sdk/integrations/agent-skill.md)); neither is used here.

## Gotchas

- **The simulator also stops when the resident's goal is met,** not only on the stopping criteria. A goal like "say you are leaving" ends the call before the agent records. Every goal now ends with "stay on the line until it says goodbye".
- **An empty agent answer ends the simulation,** and the SDK marks that turn FAILED. After `end_call` our callback answers empty on purpose, so a session that ends that way shows one failed turn.
- **`agent_goes_first=True` ignores the test case's `input`,** so the CSV leaves it empty ([Simulate Conversation](https://docs.galtea.ai/sdk/api/simulator/simulate.md)).
- **No product creation in the SDK.** The REST API does it; so does the dashboard.
- Galtea has a no-code [SLNG.ai integration](https://docs.galtea.ai/sdk/integrations/slng.md) (an endpoint connection to the Context Router). It cannot see our tool calls, so it cannot check the triage status; this eval runs the agent locally for that reason.

## Sources

- [Simulating User Conversations](https://docs.galtea.ai/sdk/tutorials/simulating-conversations.md)
- [Simulate Conversation](https://docs.galtea.ai/sdk/api/simulator/simulate.md) and [AgentInput](https://docs.galtea.ai/sdk/api/agent/input.md)
- [Behavior Datasets](https://docs.galtea.ai/concepts/product/dataset/behavior-datasets.md) and [Create a Custom Dataset](https://docs.galtea.ai/sdk/tutorials/create-dataset.md)
- [Create Test Case](https://docs.galtea.ai/sdk/api/test-case/create.md), [Create Session](https://docs.galtea.ai/sdk/api/session/create.md), [Create Version](https://docs.galtea.ai/sdk/api/version/create.md)
- [Product Service](https://docs.galtea.ai/sdk/api/product/service.md) and [Create product (REST)](https://docs.galtea.ai/api-reference/products/create-product.md)
- [SLNG.ai integration](https://docs.galtea.ai/sdk/integrations/slng.md)
- [galtea on PyPI](https://pypi.org/project/galtea/)
- The docs index for coding agents: https://docs.galtea.ai/llms.txt
