"""Compute the active scenario's lead time from its cached hotspots, spread and zones.

    pnpm data:lead-time            # the scenario HACKFIRE_SCENARIO names (the demo's: La Atalaya)
    pnpm data:lead-time --check    # recompute and compare with the file; writes nothing

No network and no key. Writes the scenario's lead-time file (the demo's: data/lead_time_la-atalaya.json),
which GET /api/lead-time serves and the pitch quotes. The zone and the definition of "reached" are the
scenario's `lead_time`: a satellite hotspot within `radius_km` of the zone's outline.

For the demo, 3 km is the pixel size of MTG, the sensor behind 62% of the hotspots; a smaller radius
depends on a single 1 km pixel from another sensor (2 km: Sentinel-3A, 8 h) and inside the outline never
happens in the data (closest 0.52 km, a day later). The bigger the radius, the shorter and the safer the
number. Applied the same way to "flagged" would be wrong: a flag is the model's prediction, not a hotspot.
"""

import json
import sys

from .. import impact
from ..lead_time import lead_time
from ..scenario import current
from .common import OutputDiffers, read_hotspots, write_or_compare

# Norma print() in production code: a command's stdout is its interface, not a log (app/pipelines/__init__.py).


def definition(zone_name: str, zone_kind: str, radius_km: float) -> str:
    return (
        f"Lead time is the time between the first forecast that put {zone_name} in the fire's predicted path, "
        f"using only satellite hotspots observed up to that moment, and the first satellite hotspot within "
        f"{radius_km:g} km of the {zone_kind.replace('_', ' ')}'s outline. It is computed from satellite data "
        f"only and says nothing about when the authorities warned anyone."
    )


def iso(moment) -> str:
    return moment.strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> None:
    scenario = current()
    radius_km = scenario.lead_time_radius_km
    zone = impact.zones().get(scenario.lead_time_zone)
    if zone is None:
        raise SystemExit(f"No zone {scenario.lead_time_zone!r} in {scenario.files.zones}: run pnpm data:zones")
    name = zone.name or zone.id
    result = lead_time(read_hotspots(), impact.forecasts(), zone, radius_km)
    if result is None:
        raise SystemExit(f"No lead time: {name} was never flagged in advance or never reached")

    body = (
        json.dumps(
            {
                "zone": zone.id,
                "zone_name": zone.name,
                "radius_km": radius_km,
                "flagged_at": iso(result.flagged_at),
                "reached_at": iso(result.reached_at),
                "minutes": result.minutes,
                "reached_by": {
                    "source": result.reached_by.source,
                    "confidence": result.reached_by.confidence,
                    "distance_km": round(result.distance_km, 2),
                },
                "definition": definition(name, zone.kind, radius_km),
            },
            indent=2,
        )
        + "\n"
    )
    write_or_compare(scenario.files.lead_time, body, f"{name}'s lead time", "--check" in sys.argv)
    print(f"flagged {iso(result.flagged_at)}, reached {iso(result.reached_at)}: {result.minutes} minutes")
    print(f"reached by {result.reached_by.source} ({result.reached_by.confidence}) at {result.distance_km:.2f} km")


if __name__ == "__main__":
    try:
        main()
    except OutputDiffers:
        # Recommended by Norma — fixed with Claude Opus 5 via Claude Code
        # write_or_compare printed the difference; the entry point owns the exit code.
        raise SystemExit(1) from None
