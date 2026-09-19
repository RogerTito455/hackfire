from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import Response

from . import replay
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


@app.post("/tools/get_evacuation_route")
def get_evacuation_route(request: EvacuationRouteRequest) -> Route:
    # TODO(map): call openrouteservice with avoid_polygons set to the predicted
    # fire polygon, clipped to the 15 km demo box (ORS limit: 20 km extent).
    profile = "by car" if request.mode == TravelMode.CAR else "on foot"
    return Route(
        mode=request.mode,
        spoken_directions=f"Route {profile} from {request.address} is not available yet.",
        stub=True,
    )


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
    # TODO(map): same routing call as get_evacuation_route, from the crew base.
    return Route(
        mode=TravelMode.CAR,
        spoken_directions=f"Route to {rescue.neighbor.address} is not available yet.",
        stub=True,
    )
