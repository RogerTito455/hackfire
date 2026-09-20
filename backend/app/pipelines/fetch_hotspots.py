"""Download Deepfire hotspots for the active scenario's box and replay window, cached as static GeoJSON.

    pnpm data:hotspots    # the scenario HACKFIRE_SCENARIO names (the demo's by default)

Needs DEEPFIRE_CLIENT_ID and DEEPFIRE_CLIENT_SECRET. Writes the scenario's hotspots file. First run for
the demo, on 2026-09-19: 7,068 hotspots, all in one cluster (the Burgohondo fire), no 3-hour window
near the 10,000-feature cap.
"""

import json
import sys
from datetime import timedelta

import httpx

from ..providers import deepfire
from ..scenario import current

# Norma print() in production code: a command's stdout is its interface, not a log (app/pipelines/__init__.py).

WINDOW = timedelta(hours=3)
# Recommended by Norma — fixed with Claude Opus 5 via Claude Code
# Deepfire runs on shared capacity and a window of 3 hours can be thousands of features.
DEEPFIRE_TIMEOUT_SECONDS = 40

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


def bbox_parameter(bbox: tuple[float, float, float, float]) -> str:
    """The box as Deepfire takes it: min lon, min lat, max lon, max lat."""
    return ",".join(str(value) for value in bbox)


def main() -> None:
    scenario = current()
    bbox, end, output = bbox_parameter(scenario.bbox), scenario.replay_end, scenario.files.hotspots
    features: list[dict] = []
    with httpx.Client(timeout=DEEPFIRE_TIMEOUT_SECONDS) as client:  # Recommended by Norma — fixed with Claude Opus 5 via Claude Code
        token = deepfire.get_token(client)
        cursor = scenario.replay_start
        while cursor < end:
            window_end = min(cursor + WINDOW, end)
            batch = deepfire.hotspots_between(client, token, bbox, cursor, window_end)
            print(f"{cursor:%Y-%m-%d %H:%M} → {len(batch)} hotspots")
            if len(batch) >= deepfire.PAGE_LIMIT:
                print("  warning: hit the feature cap; shorten WINDOW", file=sys.stderr)
            features.extend(batch)
            cursor = window_end

    # Sorted by time so the file diffs cleanly and the replay can binary-search it.
    features = sorted((compact(f) for f in features), key=lambda f: (f["properties"]["observed_at"], f["id"]))
    output.write_text(
        json.dumps({"type": "FeatureCollection", "features": features}, separators=(",", ":")),
        encoding="utf-8",
    )
    print(f"wrote {len(features)} hotspots to {output}")


if __name__ == "__main__":
    main()
