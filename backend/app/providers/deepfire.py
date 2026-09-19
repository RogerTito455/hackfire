"""Deepfire API client. Request shapes follow https://docs.deepfire.co/llms.txt.

Hotspots and active clusters verified against the live API on 2026-09-19.
"""

from datetime import datetime

import httpx

from ..config import settings

API = "https://api.deepfire.co"
_ITEMS = API + "/ogc/features/v1/collections/deepfire:{collection}/items"
_TIMESTAMP = "%Y-%m-%dT%H:%M:%SZ"

# The API caps a response at 10,000 features and has no sortby, so callers walk time windows.
PAGE_LIMIT = 10_000


def get_token(client: httpx.Client) -> str:
    """Exchange the API client for a bearer token. Tokens last 180 days; cache them."""
    response = client.post(
        f"{API}/v1/token",
        json={
            "client_id": settings.deepfire_client_id,
            "client_secret": settings.deepfire_client_secret,
        },
    )
    response.raise_for_status()
    return response.json()["access_token"]


_token: str | None = None


def cached_token(client: httpx.Client) -> str:
    """A token reused for the life of the process: they last 180 days."""
    global _token
    if _token is None:
        _token = get_token(client)
    return _token


def _items(client: httpx.Client, token: str, collection: str, bbox: str, cql: str) -> list[dict]:
    response = client.get(
        _ITEMS.format(collection=collection),
        headers={"Authorization": f"Bearer {token}"},
        params={
            "bbox": bbox,
            "filter-lang": "cql2-text",
            "filter": cql,
            "limit": PAGE_LIMIT,
            "f": "application/geo+json",
        },
    )
    response.raise_for_status()
    return response.json().get("features", [])


def hotspots_between(
    client: httpx.Client, token: str, bbox: str, start: datetime, end: datetime
) -> list[dict]:
    cql = (
        f"observed_at >= TIMESTAMP('{start.strftime(_TIMESTAMP)}') "
        f"AND observed_at < TIMESTAMP('{end.strftime(_TIMESTAMP)}')"
    )
    return _items(client, token, "hotspots", bbox, cql)


def active_clusters(client: httpx.Client, token: str, bbox: str) -> list[dict]:
    return _items(client, token, "clusters", bbox, "active = true")


# Fire spread simulations. Deepfire runs ELMFIRE on its own on active fires (`auto: true`); these read
# those runs and never queue one (only two may be in flight per API client). Verified 2026-09-19.
_SIMULATIONS = API + "/v1/fire-spread/simulations"
SIMULATIONS_PAGE = 100


def simulations_since(client: httpx.Client, token: str, since: datetime, max_pages: int) -> list[dict]:
    """The organisation's simulations created since `since`, newest first, at most `max_pages` pages.

    List items carry no `result`; fetch each simulation for its hourly polygons.
    """
    items: list[dict] = []
    params: dict[str, str | int] = {"since": since.strftime(_TIMESTAMP), "limit": SIMULATIONS_PAGE}
    for _ in range(max_pages):
        response = client.get(_SIMULATIONS, headers={"Authorization": f"Bearer {token}"}, params=params)
        response.raise_for_status()
        body = response.json()
        items.extend(body.get("items", []))
        cursor = body.get("nextCursor")
        if not cursor:
            break
        params = {**params, "cursor": cursor}
    return items


def simulation(client: httpx.Client, token: str, simulation_id: str) -> dict:
    """One simulation. Once `COMPLETED`, `result` is a FeatureCollection with one cumulative
    MultiPolygon per hour (`hour`, `elapsed_seconds`, and `burn_probability` for ensembles)."""
    response = client.get(f"{_SIMULATIONS}/{simulation_id}", headers={"Authorization": f"Bearer {token}"})
    response.raise_for_status()
    return response.json()


def configured() -> bool:
    return bool(settings.deepfire_client_id and settings.deepfire_client_secret)


def ping(client: httpx.Client) -> int:
    """For the status page (app/provider_status.py): the status code of a one-feature read of the
    active clusters, after the token. A refused token raises httpx.HTTPStatusError."""
    token = cached_token(client)
    response = client.get(
        _ITEMS.format(collection="clusters"),
        headers={"Authorization": f"Bearer {token}"},
        params={"limit": 1, "f": "application/geo+json"},
    )
    return response.status_code
