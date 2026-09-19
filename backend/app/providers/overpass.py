"""Overpass API client (OpenStreetMap data). Public and keyless, but shared: fetch once, cache in data/."""

import httpx

from ..config import settings

# Overpass operators ask clients to identify themselves.
_HEADERS = {"User-Agent": "hackfire-hackbarna/0.1 (wildfire evacuation demo)"}


def elements(client: httpx.Client, query: str) -> list[dict]:
    """Run an Overpass QL query and return its elements."""
    response = client.post(settings.overpass_url, data={"data": query}, headers=_HEADERS)
    response.raise_for_status()
    return response.json()["elements"]
