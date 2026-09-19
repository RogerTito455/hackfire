"""Overpass API client (OpenStreetMap data). Public and keyless, but shared: fetch once, cache in data/."""

import time

import httpx

from ..config import settings

# Overpass operators ask clients to identify themselves.
_HEADERS = {"User-Agent": "hackfire-hackbarna/0.1 (wildfire evacuation demo)"}


def servers() -> list[str]:
    """OVERPASS_URL, then the mirrors, each once."""
    return list(dict.fromkeys([settings.overpass_url, *settings.overpass_mirrors]))


def elements(client: httpx.Client, query: str, deadline: float | None = None) -> list[dict]:
    """Run an Overpass QL query and return its elements.

    A busy (429, 504) or unreachable server passes the query on to the next mirror, until one answers
    or `deadline` (time.monotonic()) has passed; then the last error is raised.
    """
    error: httpx.HTTPError | None = None
    for url in servers():
        if error is not None and deadline is not None and time.monotonic() >= deadline:
            break
        try:
            response = client.post(url, data={"data": query}, headers=_HEADERS)
            response.raise_for_status()
            return response.json()["elements"]
        except httpx.HTTPError as failure:
            error = failure
    assert error is not None, "no Overpass server configured"
    raise error


def ping(client: httpx.Client, url: str) -> int:
    """For the status page (app/provider_status.py): the status code of the smallest query there is."""
    response = client.get(url, params={"data": "[out:json][timeout:3];node(1);out ids;"}, headers=_HEADERS)
    return response.status_code
