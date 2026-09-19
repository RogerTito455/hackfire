"""Nebius Token Factory client. The API is OpenAI-compatible.

NEBIUS_BASE_URL is https://api.tokenfactory.nebius.com/v1 (from the quickstart).
Pick NEBIUS_MODEL from the catalogue at https://tokenfactory.nebius.com.
"""

import httpx

from ..config import settings


def complete(client: httpx.Client, messages: list[dict], **params) -> dict:
    """One chat completion. Returns the assistant message, tool calls included."""
    response = client.post(
        f"{settings.nebius_base_url.rstrip('/')}/chat/completions",
        headers={"Authorization": f"Bearer {settings.nebius_api_key}"},
        json={"model": settings.nebius_model, "messages": messages, **params},
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]


def chat(client: httpx.Client, messages: list[dict], **params) -> str:
    return complete(client, messages, **params)["content"]
