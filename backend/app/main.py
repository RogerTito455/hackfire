from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import Response

from . import impact, replay
from .config import settings
from .models import (
    EvacuationRouteRequest,
    FireStatus,
    FireStatusRequest,
    Neighbor,
    ReplayTimeRequest,
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


@app.get("/api/spread")
def get_spread() -> Response:
    """Predicted spread for 23 July: one polygon per hour ahead, for each forecast issued."""
    body = replay.spread_geojson()
    if body is None:
        raise HTTPException(status_code=404, detail="No cached spread: run pnpm data:spread")
    return Response(content=body, media_type="application/geo+json")


@app.get("/api/zones")
def get_zones() -> Response:
    """Towns, care homes, schools, health centres and main roads from OpenStreetMap."""
    body = replay.zones_geojson()
    if body is None:
        raise HTTPException(status_code=404, detail="No cached zones: run pnpm data:zones")
    return Response(content=body, media_type="application/geo+json")


@app.get("/api/impact")
def get_impact() -> dict:
    """Forecast in force and minutes to impact per zone at every 5 minutes of the replay."""
    table = impact.timeline()
    if table is None:
        raise HTTPException(status_code=404, detail="No cached spread: run pnpm data:spread")
    return table


@app.post("/api/replay/time")
def set_replay_time(request: ReplayTimeRequest) -> dict:
    """The dashboard's slider moved: the agent's answers now refer to this replay moment."""
    state.replay_time = request.at
    return {"at": request.at}


@app.post("/api/reset")
def reset() -> dict:
    """Reload the registry. Used to restart the demo."""
    state.load()
    return {"status": "reset", "neighbors": len(state.neighbors())}


# --- Agent tools -------------------------------------------------------------
# The contract between the voice agent and everything else. See PLAN.md section 6.


@app.post("/tools/get_fire_status")
def get_fire_status(request: FireStatusRequest) -> FireStatus:
    """Answers for the replay moment the dashboard's slider is on, from the same numbers as its panel."""
    minutes = state.minutes_to_impact(request.zone)
    return FireStatus(
        zone=request.zone,
        at_risk=minutes is not None,
        minutes_to_impact=minutes,
        summary=_fire_summary(request.zone, minutes),
    )


def _spoken_span(minutes: int) -> str:
    """"25 minutes" or "3 hours", rounded down: a lead time is never overstated to a resident."""
    if minutes < 90:
        return f"{max(5, 5 * (minutes // 5))} minutes"
    hours = minutes // 60
    return f"{hours} hour" if hours == 1 else f"{hours} hours"


def _fire_summary(zone: str, minutes: int | None) -> str:
    name = impact.zone_name(zone)
    if minutes is None:
        horizon = impact.remaining_horizon_minutes(state.clock())
        if horizon is None:
            return f"There is no forecast for this moment, so nothing is predicted for {name}."
        return f"No predicted impact on {name} in the next {_spoken_span(horizon)}."
    if minutes == 0:
        return f"The predicted fire area already covers {name}."
    return f"The fire is predicted to reach {name} in about {_spoken_span(minutes)}."


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
