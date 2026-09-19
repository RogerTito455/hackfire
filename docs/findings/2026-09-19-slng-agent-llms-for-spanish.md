# Which LLMs an SLNG agent accepts for Spanish in Europe

**Date:** 2026-09-19 · **Area:** SLNG

## What happened

SLNG's API reference lists three values for an agent's `models.llm`: `bedrock-mantle/nvidia.nemotron-super-3-120b`, `bedrock-mantle/nvidia.nemotron-nano-3-30b` and `groq/openai/gpt-oss-120b`. Deploying the resident agent with `groq/openai/gpt-oss-120b` failed with `400 AGENT_MODEL_UNAVAILABLE`. There is no endpoint that lists the LLMs an agent may use (`/v1/catalog/models` covers speech only), so we created throwaway agents (`language: es`) with each candidate and deleted them:

| `models.llm` | eu-north | eu-west |
|---|---|---|
| `bedrock-mantle/nvidia.nemotron-super-3-120b:latest` | accepted | accepted |
| `bedrock-mantle/nvidia.nemotron-nano-3-30b:latest` | accepted | not tried |
| the two Nemotron ids without `:latest` | `not available for agents` | not tried |
| `groq/openai/gpt-oss-120b:latest` | `not allowed for region 'eu-north' and language 'es'` | same for `eu-west` |
| `groq/openai/gpt-oss-120b`, `slng/auto` | `not available for agents` | not tried |

## Why

Not verified. The documented ids lack the `:latest` suffix the API now requires, and each model is allowed per region and language.

## What we do about it

For #7: the team dropped Nebius for the agent, and it runs on Nemotron Super 3. Nano 3 is the switch if turns feel slow once we measure them (#14). Later the same day the team dropped Nebius from the whole stack: `providers/llm.py` and `pnpm eval:triage` now reach this same model through SLNG's Context Router.

## Sources

- https://docs.slng.ai/api-reference/agents/create-agent.md
- https://docs.slng.ai/guides/agents/configure/think.md
