"""Download Deepfire hotspots for the demo box and cache them as static GeoJSON.

    pnpm data:hotspots

Needs DEEPFIRE_CLIENT_ID and DEEPFIRE_CLIENT_SECRET. Not yet run against the live API.
"""

import json
import sys
from datetime import UTC, datetime, timedelta

import httpx

from ..config import DATA_DIR
from ..providers import deepfire

# Demo box around Burgohondo, El Tiemblo and La Atalaya (min lon, min lat, max lon, max lat).
BBOX = "-4.85,40.30,-4.40,40.50"
START = datetime(2026, 7, 22, tzinfo=UTC)
END = datetime(2026, 7, 25, tzinfo=UTC)
WINDOW = timedelta(hours=3)

OUTPUT = DATA_DIR / "hotspots_2026-07-22_24.geojson"


def main() -> None:
    features: list[dict] = []
    with httpx.Client(timeout=40) as client:
        token = deepfire.get_token(client)
        cursor = START
        while cursor < END:
            window_end = min(cursor + WINDOW, END)
            batch = deepfire.hotspots_between(client, token, BBOX, cursor, window_end)
            print(f"{cursor:%Y-%m-%d %H:%M} → {len(batch)} hotspots")
            if len(batch) >= deepfire.PAGE_LIMIT:
                print("  warning: hit the feature cap; shorten WINDOW", file=sys.stderr)
            features.extend(batch)
            cursor = window_end

    OUTPUT.write_text(json.dumps({"type": "FeatureCollection", "features": features}), encoding="utf-8")
    print(f"wrote {len(features)} hotspots to {OUTPUT}")


if __name__ == "__main__":
    main()
