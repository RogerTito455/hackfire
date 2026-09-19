"""The active scenario: which fire is replayed, where, when, and from which files.

A scenario is one JSON file, `data/scenarios/<id>.json`, picked by HACKFIRE_SCENARIO (an id, or a path
to a scenario file). It holds everything that used to be a constant about 23 July 2026 near El Tiemblo:
the bounding box, the replay window, the forecast day, the scenario time, the lead-time zone, the named
places `pnpm data:zones` draws, and the data files. Paths in it are relative to the file itself.
See docs/setup/new-scenario.md.

One scenario is active per process. Everything read from its files is cached with `cached`, which
`activate` clears, so tests can switch to another scenario (backend/tests/fixtures/) and back.
"""

import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from functools import cache
from pathlib import Path
from typing import TypeVar

import shapely
from shapely.geometry.base import BaseGeometry

from .config import DATA_DIR, REPO_ROOT, settings

SCENARIOS_DIR = DATA_DIR / "scenarios"


@dataclass(frozen=True)
class NamedPlace:
    """A town or estate `pnpm data:zones` draws from the residential land use around its OSM node:
    the zones the registry's residents belong to."""

    id: str
    name: str
    kind: str
    lon: float
    lat: float
    radius_m: int


@dataclass(frozen=True)
class Files:
    hotspots: Path  # pnpm data:hotspots
    spread: Path  # pnpm data:spread
    zones: Path  # pnpm data:zones
    lead_time: Path  # pnpm data:lead-time
    places: Path  # safe points and the crew base, by hand
    routes: Path  # pnpm data:routes
    registry: Path  # the tracked resident registry (placeholder phones)
    local_registry: Path | None  # the git-ignored one with real phones, which wins when it exists
    timeline: Path  # the demo autopilot's script
    calls: Path  # recorded calls the autopilot shows


@dataclass(frozen=True)
class Scenario:
    id: str
    name: str
    # min lon, min lat, max lon, max lat. Every cached polygon is clipped to it; the map fits it.
    bbox: tuple[float, float, float, float]
    # The time zone the dashboard shows replay times in (IANA name).
    time_zone: str
    # The hotspots `pnpm data:hotspots` downloads: from `replay_start` up to, not including, `replay_end`.
    replay_start: datetime
    replay_end: datetime
    # The forecasts `pnpm data:spread` issues: from the first to the last, every `forecast_every`.
    forecast_first: datetime
    forecast_last: datetime
    forecast_every: timedelta
    # The replay moment the calls happen at: routes avoid the fire burned up to then.
    scenario_time: datetime
    # The zone whose lead time is the headline number, and how near a hotspot counts as "reached".
    lead_time_zone: str
    lead_time_radius_km: float
    places: tuple[NamedPlace, ...]
    files: Files

    @property
    def box(self) -> BaseGeometry:
        return shapely.box(*self.bbox)

    @property
    def centre_lat(self) -> float:
        return (self.bbox[1] + self.bbox[3]) / 2


def _time(value: str) -> datetime:
    moment = datetime.fromisoformat(value)
    if moment.tzinfo is None:
        raise ValueError(f"{value!r} has no time zone: write it in UTC, ending in Z")
    return moment


def parse(raw: dict, base: Path, scenario_time: datetime | None = None) -> Scenario:
    """A scenario from its JSON, with paths resolved against `base` (the file's directory).
    `scenario_time`, when given, replaces the file's (HACKFIRE_SCENARIO_TIME)."""
    files = raw["files"]

    def file(key: str) -> Path:
        return (base / files[key]).resolve()

    bbox = tuple(float(v) for v in raw["bbox"])
    if len(bbox) != 4 or bbox[0] >= bbox[2] or bbox[1] >= bbox[3]:
        raise ValueError(f"scenario {raw.get('id')}: bbox must be [min lon, min lat, max lon, max lat]")
    lead_time = raw["lead_time"]
    return Scenario(
        id=raw["id"],
        name=raw["name"],
        bbox=bbox,  # type: ignore[arg-type]
        time_zone=raw.get("time_zone", "UTC"),
        replay_start=_time(raw["replay"]["start"]),
        replay_end=_time(raw["replay"]["end"]),
        forecast_first=_time(raw["forecasts"]["first"]),
        forecast_last=_time(raw["forecasts"]["last"]),
        forecast_every=timedelta(minutes=float(raw["forecasts"]["every_minutes"])),
        scenario_time=scenario_time or _time(raw["scenario_time"]),
        lead_time_zone=lead_time["zone"],
        lead_time_radius_km=lead_time["radius_km"],
        places=tuple(
            NamedPlace(p["id"], p["name"], p["kind"], float(p["lon"]), float(p["lat"]), int(p["radius_m"]))
            for p in raw.get("places", [])
        ),
        files=Files(
            hotspots=file("hotspots"),
            spread=file("spread"),
            zones=file("zones"),
            lead_time=file("lead_time"),
            places=file("places"),
            routes=file("routes"),
            registry=file("registry"),
            local_registry=file("local_registry") if files.get("local_registry") else None,
            timeline=file("timeline"),
            calls=file("calls"),
        ),
    )


def path_of(name: str) -> Path:
    """The file of a scenario given by id (data/scenarios/<id>.json) or by a path to a .json file,
    relative to the repo root (the backend runs from backend/)."""
    candidate = Path(name).expanduser()
    if candidate.suffix == ".json":
        return candidate if candidate.is_absolute() else REPO_ROOT / candidate
    return SCENARIOS_DIR / f"{name}.json"


def load(path: Path, scenario_time: datetime | None = None) -> Scenario:
    path = path.resolve()
    return parse(json.loads(path.read_text(encoding="utf-8")), path.parent, scenario_time)


_active: Scenario | None = None
_on_change: list[Callable[[], None]] = []


def current() -> Scenario:
    """The active scenario: HACKFIRE_SCENARIO's, until `activate` sets another."""
    global _active
    if _active is None:
        _active = load(path_of(settings.scenario), settings.scenario_time_override)
    return _active


def activate(scenario: Scenario) -> None:
    """Make `scenario` the active one and forget everything read from the previous one's files."""
    global _active
    _active = scenario
    for forget in _on_change:
        forget()


def on_change(forget: Callable[[], None]) -> None:
    """Call `forget` whenever another scenario becomes active: for state built from its files."""
    _on_change.append(forget)


F = TypeVar("F", bound=Callable)


def cached(function: F) -> F:
    """`functools.cache`, cleared when another scenario becomes active."""
    memo = cache(function)
    on_change(memo.cache_clear)
    return memo  # type: ignore[return-value]
