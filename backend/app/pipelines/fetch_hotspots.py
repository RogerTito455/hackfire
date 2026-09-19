"""Download Deepfire hotspots for the demo box and cache them as static GeoJSON.

    pnpm data:hotspots

Needs DEEPFIRE_CLIENT_ID and DEEPFIRE_CLIENT_SECRET. First run on 2026-09-19: 7,068 hotspots,
all in one cluster (the Burgohondo fire), no 3-hour window near the 10,000-feature cap.
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

# What the replay needs from each hotspot; the rest of Deepfire's properties are dropped.
KEEP = ("observed_at", "fire_radiative_power", "confidence", "source", "cluster_id")


def compact(feature: dict) -> dict:
    """Keep the replay's properties and round coordinates to 5 decimals (about 1 m)."""
    lon, lat = feature["geometry"]["coordinates"][:2]
    properties = {key: feature["properties"].get(key) for key in KEEP}
    if properties["fire_radiative_power"] is not None:
        properties["fire_radiative_power"] = round(properties["fire_radiative_power"], 1)
    return {
        "type": "Feature",
        "id": feature["id"],
        "geometry": {"type": "Point", "coordinates": [round(lon, 5), round(lat, 5)]},
        "properties": properties,
    }


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

    # Sorted by time so the file diffs cleanly and the replay can binary-search it.
    features = sorted((compact(f) for f in features), key=lambda f: (f["properties"]["observed_at"], f["id"]))
    OUTPUT.write_text(
        json.dumps({"type": "FeatureCollection", "features": features}, separators=(",", ":")),
        encoding="utf-8",
    )
    print(f"wrote {len(features)} hotspots to {OUTPUT}")


if __name__ == "__main__":
    main()
