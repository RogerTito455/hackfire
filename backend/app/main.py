from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles

from . import evacuation, live, replay
from .config import settings
from .models import (
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


@app.get("/api/fire-area")
def fire_area() -> dict:
    """The area routes avoid: everything burned up to the scenario time."""
    return evacuation.fire_area()


@app.post("/api/reset")
def reset() -> dict:
    """Reload the registry. Used to restart the demo."""
    state.load()
    return {"status": "reset", "neighbors": len(state.neighbors())}


# --- Agent tools -------------------------------------------------------------
# The contract between the voice agent and everything else. See PLAN.md section 6.


@app.post("/tools/get_fire_status")
def get_fire_status(request: FireStatusRequest) -> FireStatus:
    # TODO(data): answer from the cached Deepfire spread for the replay timestamp.
    minutes = state.minutes_to_impact(request.zone)
    return FireStatus(
        zone=request.zone,
        at_risk=minutes is not None,
        minutes_to_impact=minutes,
        summary=(
            f"The fire is predicted to reach {request.zone} in about {minutes} minutes."
            if minutes is not None
            else f"No predicted impact on {request.zone}."
        ),
        stub=True,
    )


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
    # TODO(voice): when status is needs_rescue, notify the fire crew by SMS or call.
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
