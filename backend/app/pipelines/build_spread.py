"""Build the predicted spread for the replay of 23 July 2026 from the cached hotspots.

    pnpm data:spread

Reads data/hotspots_2026-07-22_24.geojson, writes data/spread_2026-07-23.geojson. No network and
no key: the model is in app/spread.py. A forecast is issued every 30 minutes of the UTC day; each
one contributes a polygon for now (hour 0) and one per hour ahead, all tagged with `issued_at`.
Times with too few recent hotspots (for example the satellite gap on the afternoon of 23 July)
get no forecast.
"""

import json
from datetime import UTC, datetime, timedelta

import shapely
from shapely.geometry import mapping

from ..config import DATA_DIR
from ..impact import HORIZON_HOURS
from ..replay import DEMO_BOX
from ..spread import forecast
from .common import read_hotspots

OUTPUT = DATA_DIR / "spread_2026-07-23.geojson"

FIRST_ISSUE = datetime(2026, 7, 23, 0, 0, tzinfo=UTC)
LAST_ISSUE = datetime(2026, 7, 23, 23, 30, tzinfo=UTC)
ISSUE_EVERY = timedelta(minutes=30)

# Polygons are clipped to the demo box, simplified to about 30 m and snapped to a ~1 m grid: the model is not that precise.
SIMPLIFY_DEG = 0.0003
COORDINATE_GRID_DEG = 0.00001


def main() -> None:
    hotspots = read_hotspots()
    features = []
    issued = 0
    moment = FIRST_ISSUE
    while moment <= LAST_ISSUE:
        result = forecast(hotspots, moment, HORIZON_HOURS)
        if result is None:
            print(f"{moment:%H:%M} no forecast")
        else:
            issued += 1
            for hour, area in enumerate(result.spread):
                area = shapely.set_precision(
                    area.intersection(DEMO_BOX).simplify(SIMPLIFY_DEG), COORDINATE_GRID_DEG
                )
                features.append(
                    {
                        "type": "Feature",
                        "geometry": mapping(area),
                        "properties": {
                            "issued_at": moment.strftime("%Y-%m-%dT%H:%M:%SZ"),
                            "hour": hour,
                            "heading_deg": None if result.heading_deg is None else round(result.heading_deg),
                            "speed_kmh": round(result.speed_kmh, 1),
                        },
                    }
                )
        moment += ISSUE_EVERY

    OUTPUT.write_text(
        json.dumps({"type": "FeatureCollection", "features": features}, separators=(",", ":")),
        encoding="utf-8",
    )
    print(f"wrote {issued} forecasts ({len(features)} polygons) to {OUTPUT}")


if __name__ == "__main__":
    main()
