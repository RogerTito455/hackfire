"""Nebius Token Factory client. The API is OpenAI-compatible.

Set NEBIUS_BASE_URL and NEBIUS_MODEL from https://docs.tokenfactory.nebius.com/quickstart;
they are deliberately not hard-coded here because we have not confirmed them.
"""

import httpx

from ..config import settings


def chat(client: httpx.Client, messages: list[dict], **params) -> str:
    response = client.post(
        f"{settings.nebius_base_url.rstrip('/')}/chat/completions",
        headers={"Authorization": f"Bearer {settings.nebius_api_key}"},
        json={"model": settings.nebius_model, "messages": messages, **params},
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]
