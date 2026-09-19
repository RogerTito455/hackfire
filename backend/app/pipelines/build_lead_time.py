"""Compute La Atalaya's lead time from the cached hotspots, spread and zones.

    pnpm data:lead-time

No network and no key. Writes data/lead_time_la-atalaya.json, which GET /api/lead-time serves and
the pitch quotes. The definition of "reached" is chosen once, here: see RADIUS_KM.
"""

import json

from .. import impact
from ..config import DATA_DIR
from ..lead_time import lead_time
from .common import read_hotspots

OUTPUT = DATA_DIR / "lead_time_la-atalaya.json"
ZONE = "la-atalaya"

# "The fire reached La Atalaya" means a satellite hotspot within 3 km of the estate's outline. 3 km is
# the pixel size of MTG, the sensor behind 62% of the hotspots; a smaller radius depends on a single
# 1 km pixel from another sensor (2 km: Sentinel-3A, 8 h) and inside the outline never happens in the
# data (closest 0.52 km, a day later). The bigger the radius, the shorter and the safer the number.
# Applied the same way to "flagged" would be wrong: a flag is the model's prediction, not a hotspot.
RADIUS_KM = 3

DEFINITION = (
    f"Lead time is the time between the first forecast that put La Atalaya in the fire's predicted path, "
    f"using only satellite hotspots observed up to that moment, and the first satellite hotspot within "
    f"{RADIUS_KM} km of the estate's outline. It is computed from satellite data only and says nothing "
    f"about when the authorities warned anyone."
)


def iso(moment) -> str:
    return moment.strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> None:
    zone = impact.zones()[ZONE]
    result = lead_time(read_hotspots(), impact.forecasts(), zone, RADIUS_KM)
    if result is None:
        raise SystemExit("No lead time: La Atalaya was never flagged in advance or never reached")

    OUTPUT.write_text(
        json.dumps(
            {
                "zone": ZONE,
                "zone_name": zone.name,
                "radius_km": RADIUS_KM,
                "flagged_at": iso(result.flagged_at),
                "reached_at": iso(result.reached_at),
                "minutes": result.minutes,
                "reached_by": {
                    "source": result.reached_by.source,
                    "confidence": result.reached_by.confidence,
                    "distance_km": round(result.distance_km, 2),
                },
                "definition": DEFINITION,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"flagged {iso(result.flagged_at)}, reached {iso(result.reached_at)}: {result.minutes} minutes")
    print(f"reached by {result.reached_by.source} ({result.reached_by.confidence}) at {result.distance_km:.2f} km")


if __name__ == "__main__":
    main()
