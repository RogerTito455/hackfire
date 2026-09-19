"""The backend's LLM: SLNG's Context Router, an OpenAI-compatible Chat Completions endpoint.

Same key (SLNG_API_KEY) and same model as the voice agents, so a typed answer is triaged by the
model that triages a call. The router requires an agent id, which scopes its cache (change it when
the system prompt changes), and a session id per conversation.
See https://docs.slng.ai/api-reference/context-router/chat-completions.md
"""

import uuid

import httpx

from ..config import settings


def configured() -> bool:
    return bool(settings.slng_api_key and settings.slng_llm_model)


def complete(client: httpx.Client, messages: list[dict], *, agent_id: str, **params) -> dict:
    """One chat completion. Returns the assistant message, tool calls included."""
    response = client.post(
        f"{settings.slng_llm_url}/chat/completions",
        headers={
            "Authorization": f"Bearer {settings.slng_api_key}",
            "X-Slng-Agent-Id": agent_id,
            "X-Slng-Session-Id": uuid.uuid4().hex,
        },
        json={"model": settings.slng_llm_model, "messages": messages, **params},
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]


def chat(client: httpx.Client, messages: list[dict], *, agent_id: str, **params) -> str:
    return complete(client, messages, agent_id=agent_id, **params)["content"]
