"""Build the active scenario's predicted spread from its cached hotspots.

    pnpm data:spread            # the scenario HACKFIRE_SCENARIO names (the demo's by default)
    pnpm data:spread --check    # rebuild in memory and compare with the file; writes nothing

Reads the scenario's hotspots and writes its spread (the demo: data/hotspots_2026-07-22_24.geojson to
data/spread_2026-07-23.geojson). No network and no key: the model is in app/spread.py. A forecast is
issued every `forecasts.every_minutes` from `forecasts.first` to `forecasts.last` (the demo: every 30
minutes of 23 July, UTC); each one contributes a polygon for now (hour 0) and one per hour ahead, all
tagged with `issued_at`. Times with too few recent hotspots (for example the satellite gap on the
afternoon of 23 July) get no forecast.
"""

import json
import sys

import shapely
from shapely.geometry import mapping

from ..impact import HORIZON_HOURS
from ..scenario import current
from ..spread import forecast
from .common import OutputDiffers, read_hotspots, write_or_compare

# Norma print() in production code: a command's stdout is its interface, not a log (app/pipelines/__init__.py).

# Polygons are clipped to the scenario's box, simplified to about 30 m and snapped to a ~1 m grid: the
# model is not that precise.
SIMPLIFY_DEG = 0.0003
COORDINATE_GRID_DEG = 0.00001


def main() -> None:
    scenario = current()
    box = scenario.box
    hotspots = read_hotspots()
    features = []
    issued = 0
    moment = scenario.forecast_first
    while moment <= scenario.forecast_last:
        result = forecast(hotspots, moment, HORIZON_HOURS)
        if result is None:
            print(f"{moment:%H:%M} no forecast")
        else:
            issued += 1
            for hour, area in enumerate(result.spread):
                area = shapely.set_precision(area.intersection(box).simplify(SIMPLIFY_DEG), COORDINATE_GRID_DEG)
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
        moment += scenario.forecast_every

    body = json.dumps({"type": "FeatureCollection", "features": features}, separators=(",", ":"))
    write_or_compare(scenario.files.spread, body, f"{issued} forecasts ({len(features)} polygons)", "--check" in sys.argv)


if __name__ == "__main__":
    try:
        main()
    except OutputDiffers:
        # Recommended by Norma — fixed with Claude Opus 5 via Claude Code
        # write_or_compare printed the difference; the entry point owns the exit code.
        raise SystemExit(1) from None
