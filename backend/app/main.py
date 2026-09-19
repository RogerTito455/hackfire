from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from shapely.geometry import mapping

from . import evacuation, geo, live, replay, spread, zones
from .config import settings
from .models import (
    CrewAlert,
    EvacuationRouteRequest,
    FireStatus,
    FireStatusRequest,
    Neighbor,
    ReportStatusRequest,
    Rescue,
    RescueRouteRequest,
    Route,
    TravelMode,
)
from .state import state

app = FastAPI(title="HackFire", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


# --- Dashboard API -----------------------------------------------------------


@app.get("/api/neighbors")
def list_neighbors() -> list[Neighbor]:
    return state.neighbors()


@app.get("/api/rescues")
def list_rescues() -> list[Rescue]:
    return state.rescue_queue()


@app.get("/api/hotspots")
def list_hotspots() -> Response:
    """Deepfire hotspots for the 22–24 July 2026 replay, sorted by observed_at."""
    body = replay.hotspots_geojson()
    if body is None:
        raise HTTPException(status_code=404, detail="No cached hotspots: run pnpm data:hotspots")
    return Response(content=body, media_type="application/geo+json")


@app.get("/api/live/fires")
def list_live_fires() -> dict:
    """Deepfire's active fire clusters over Iberia, cached for a minute."""
    try:
        return live.active_fires()
    except live.LiveUnavailable as error:
        raise HTTPException(status_code=503, detail="Deepfire is unavailable right now") from error


@app.get("/api/routes/{neighbor_id}")
def neighbor_route(neighbor_id: str, mode: TravelMode = TravelMode.CAR) -> Route:
    """The resident's evacuation route, for the dashboard to draw."""
    neighbor = state.get(neighbor_id)
    if neighbor is None:
        raise HTTPException(status_code=404, detail=f"Unknown neighbor {neighbor_id}")
    return _route_or_503(lambda: evacuation.evacuation_route(neighbor, mode))


@app.get("/api/rescue-routes/{neighbor_id}")
def neighbor_rescue_route(neighbor_id: str) -> Route:
    """The crew's route from the fire station to the resident, for the dashboard to draw."""
    neighbor = state.get(neighbor_id)
    if neighbor is None:
        raise HTTPException(status_code=404, detail=f"Unknown neighbor {neighbor_id}")
    return _route_or_503(lambda: evacuation.rescue_route(neighbor))


@app.get("/api/alerts")
def list_alerts() -> list[CrewAlert]:
    """Crew alerts for new rescues, newest first."""
    return state.alerts()


def _replay_time(at: datetime | None) -> datetime:
    return zones.snap(at or settings.scenario_time)


@app.get("/api/spread")
def get_spread(at: datetime | None = None) -> dict:
    """The predicted spread at `at` (default: the scenario time): one polygon per hour ahead."""
    at = _replay_time(at)
    motion = spread.front_motion(at)
    return {
        "type": "FeatureCollection",
        "features": [
            {"type": "Feature", "geometry": mapping(geo.to_degrees(area)), "properties": {"hour": hour}}
            for hour, area in reversed(spread.hourly_cone(at))
        ]
        if motion
        else [],
        "at": at.isoformat(),
        "motion": {"bearing_deg": round(motion.bearing_deg), "speed_km_h": round(motion.speed_m_per_h / 1000, 2)}
        if motion
        else None,
    }


@app.get("/api/zones")
def list_zone_shapes() -> Response:
    """Every zone's outline (static; the risk comes from /api/zones/risk)."""
    return Response(content=zones.geojson(), media_type="application/geo+json")


@app.get("/api/zones/risk")
def list_zone_risk(at: datetime | None = None) -> dict:
    """Every zone's minutes to impact at `at` (default: the scenario time), soonest first."""
    at = _replay_time(at)
    return {
        "at": at.isoformat(),
        "zones": [
            {"id": zone.id, "name": zone.name, "kind": zone.kind, "minutes_to_impact": minutes}
            for zone, minutes in zones.risk(at)
        ],
    }


@app.get("/api/fire-area")
def fire_area(crew: bool = False) -> dict:
    """The area routes avoid at the scenario time: residents' routes, or crews' with `crew=true`."""
    return evacuation.fire_area(crew=crew)


@app.post("/api/reset")
def reset() -> dict:
    """Reload the registry. Used to restart the demo."""
    state.load()
    return {"status": "reset", "neighbors": len(state.neighbors())}


# --- Agent tools -------------------------------------------------------------
# The contract between the voice agent and everything else. See PLAN.md section 6.


@app.post("/tools/get_fire_status")
def get_fire_status(request: FireStatusRequest) -> FireStatus:
    """The fire's position and heading relative to a zone, at the scenario time."""
    zone = zones.all_zones().get(request.zone)
    if zone is None:
        raise HTTPException(status_code=404, detail=f"Unknown zone {request.zone}")
    at = settings.scenario_time
    minutes = zones.minutes_to_impact(zone.id, at)
    return FireStatus(
        zone=zone.id,
        at_risk=minutes is not None,
        minutes_to_impact=minutes,
        summary=fire_summary(zone.name, minutes, zones.distance_km(zone.id, at), spread.front_motion(zones.snap(at))),
    )


_COMPASS = ("north", "north-east", "east", "south-east", "south", "south-west", "west", "north-west")


def _duration(minutes: int) -> str:
    if minutes < 60:
        return f"about {minutes} minutes"
    hours, rest = divmod(round(minutes / 10) * 10, 60)
    unit = "hour" if hours == 1 else "hours"
    return f"about {hours} {unit}" if rest == 0 else f"about {hours} {unit} and {rest} minutes"


def fire_summary(name: str, minutes: int | None, distance_km: float | None, motion: spread.FrontMotion | None) -> str:
    """Two sentences the agent can retell on a call."""
    if minutes == 0:
        return f"The fire has already reached {name}."
    where = f"The burned area is about {round(distance_km)} kilometres from {name}." if distance_km else ""
    if motion is None:
        return f"{where} The satellites do not show a clear direction of spread right now.".strip()
    heading = _COMPASS[round(motion.bearing_deg / 45) % 8]
    moving = f"The fire is moving {heading} at about {motion.speed_m_per_h / 1000:.0f} kilometres an hour."
    if minutes is None:
        return f"{where} {moving} On its current course it is not heading towards {name}.".strip()
    return f"{where} {moving} At that pace it could reach {name} in {_duration(minutes)}.".strip()


def _route_or_503(plan) -> Route:
    try:
        return plan()
    except evacuation.RoutingUnavailable as error:
        raise HTTPException(status_code=503, detail="Routing is unavailable right now") from error


@app.post("/tools/get_evacuation_route")
def get_evacuation_route(request: EvacuationRouteRequest) -> Route:
    """Route from a registered resident's home to the safe point farthest from the fire."""
    neighbor = state.find_by_address(request.address)
    if neighbor is None:
        raise HTTPException(status_code=404, detail=f"Address not in the registry: {request.address}")
    return _route_or_503(lambda: evacuation.evacuation_route(neighbor, request.mode))


@app.post("/tools/report_status")
def report_status(request: ReportStatusRequest) -> Neighbor:
    neighbor = state.report(request)
    if neighbor is None:
        raise HTTPException(status_code=404, detail=f"Unknown neighbor {request.neighbor_id}")
    # New rescues become crew alerts in state (shown on the dashboard).
    # TODO(voice): also send each new alert to settings.crew_phone by SMS through
    # providers/voice.notify_crew, once SLNG/Twilio can send messages, and set sent_by_sms.
    return neighbor


@app.post("/tools/get_rescue_queue")
def get_rescue_queue() -> list[Rescue]:
    return state.rescue_queue()


@app.post("/tools/get_rescue_route")
def get_rescue_route(request: RescueRouteRequest) -> Route:
    rescue = next((r for r in state.rescue_queue() if r.rescue_id == request.rescue_id), None)
    if rescue is None:
        raise HTTPException(status_code=404, detail=f"Unknown rescue {request.rescue_id}")
    return _route_or_503(lambda: evacuation.rescue_route(rescue.neighbor))


# --- Dashboard ---------------------------------------------------------------
# Deployed, this process also serves the built dashboard, which then calls the API on its own
# origin. Only the dashboard's own paths: a catch-all mount at "/" would swallow the API's 404s
# and trailing-slash redirects. See docs/setup/deployment.md.

if settings.dashboard_dir:
    dashboard_dir = Path(settings.dashboard_dir)
    app.mount("/assets", StaticFiles(directory=dashboard_dir / "assets"), name="dashboard-assets")

    @app.get("/", include_in_schema=False)
    def dashboard() -> FileResponse:
        return FileResponse(dashboard_dir / "index.html")

    # Vite copies frontend/public/ to the root of the build; each file there needs a route here.
    @app.get("/favicon.svg", include_in_schema=False)
    def favicon() -> FileResponse:
        return FileResponse(dashboard_dir / "favicon.svg")
