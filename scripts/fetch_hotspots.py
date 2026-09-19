"""Download Deepfire hotspots for the demo box and cache them as static GeoJSON.

Usage (from the repo root, with DEEPFIRE_CLIENT_ID / DEEPFIRE_CLIENT_SECRET set):

    uv run --project backend python scripts/fetch_hotspots.py

Not yet run against the live API: nobody on the team had a token when it was written.
Request shapes follow https://docs.deepfire.co/guides/authentication and /api/hotspots.
"""

import json
import os
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx

API = "https://api.deepfire.co"
ITEMS = f"{API}/ogc/features/v1/collections/deepfire:hotspots/items"

# Demo box around Burgohondo, El Tiemblo and La Atalaya (min lon, min lat, max lon, max lat).
BBOX = "-4.85,40.30,-4.40,40.50"
START = datetime(2026, 7, 22, tzinfo=UTC)
END = datetime(2026, 7, 25, tzinfo=UTC)

# The API caps a response at 10,000 features, has no sortby and cuts queries at 30 s,
# so we walk the period in short windows instead of paging.
WINDOW = timedelta(hours=3)
PAGE_LIMIT = 10_000

OUTPUT = Path(__file__).resolve().parents[1] / "data" / "hotspots_2026-07-22_24.geojson"


def get_token(client: httpx.Client) -> str:
    response = client.post(
        f"{API}/v1/token",
        json={
            "client_id": os.environ["DEEPFIRE_CLIENT_ID"],
            "client_secret": os.environ["DEEPFIRE_CLIENT_SECRET"],
        },
    )
    response.raise_for_status()
    return response.json()["access_token"]


def fetch_window(client: httpx.Client, token: str, start: datetime, end: datetime) -> list[dict]:
    timestamp = "%Y-%m-%dT%H:%M:%SZ"
    response = client.get(
        ITEMS,
        headers={"Authorization": f"Bearer {token}"},
        params={
            "bbox": BBOX,
            "filter-lang": "cql2-text",
            "filter": (
                f"observed_at >= TIMESTAMP('{start.strftime(timestamp)}') "
                f"AND observed_at < TIMESTAMP('{end.strftime(timestamp)}')"
            ),
            "limit": PAGE_LIMIT,
            "f": "application/geo+json",
        },
    )
    response.raise_for_status()
    features = response.json().get("features", [])
    if len(features) >= PAGE_LIMIT:
        print(f"  warning: {start:%d %H:%M} hit the {PAGE_LIMIT} cap; shorten WINDOW", file=sys.stderr)
    return features


def main() -> None:
    features: list[dict] = []
    with httpx.Client(timeout=40) as client:
        token = get_token(client)
        cursor = START
        while cursor < END:
            window_end = min(cursor + WINDOW, END)
            batch = fetch_window(client, token, cursor, window_end)
            print(f"{cursor:%Y-%m-%d %H:%M} → {len(batch)} hotspots")
            features.extend(batch)
            cursor = window_end

    OUTPUT.write_text(json.dumps({"type": "FeatureCollection", "features": features}), encoding="utf-8")
    print(f"wrote {len(features)} hotspots to {OUTPUT}")


if __name__ == "__main__":
    main()
