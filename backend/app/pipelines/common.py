"""Helpers shared by the pipelines that read the cached hotspots."""

import json
from datetime import datetime

from ..replay import HOTSPOTS_FILE
from ..spread import Hotspot


def read_hotspots() -> list[Hotspot]:
    """The cached hotspots as model inputs. Raises if `pnpm data:hotspots` has not been run: a pipeline
    must never write its output from an empty input."""
    collection = json.loads(HOTSPOTS_FILE.read_text(encoding="utf-8"))
    return [
        Hotspot(
            lon=f["geometry"]["coordinates"][0],
            lat=f["geometry"]["coordinates"][1],
            observed_at=datetime.fromisoformat(f["properties"]["observed_at"]),
            source=f["properties"]["source"],
            confidence=f["properties"]["confidence"],
        )
        for f in collection["features"]
    ]
