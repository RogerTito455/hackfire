import logging
from pathlib import Path

import httpx
from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import evacuation, impact, live, orders, replay, text_triage
from .config import settings
from .models import (
    CrewAlert,
    EvacuationOrder,
    EvacuationRouteRequest,
    FireStatus,
    FireStatusRequest,
    Neighbor,
    OrderDecision,
    ReplayTimeRequest,
    ReportStatusRequest,
    Rescue,
    RescueRouteRequest,
    Route,
    SafePoint,
    TravelMode,
)
from .providers import sms
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


@app.get("/api/lead-time")
def get_lead_time() -> Response:
    """La Atalaya's lead time and how it was computed. Written by `pnpm data:lead-time`."""
    body = replay.lead_time_json()
    if body is None:
        raise HTTPException(status_code=404, detail="No cached lead time: run pnpm data:lead-time")
    return Response(content=body, media_type="application/json")


@app.post("/api/replay/time")
def set_replay_time(request: ReplayTimeRequest) -> dict:
    """The dashboard's slider moved: the agent's answers now refer to this replay moment."""
    state.replay_time = request.at
    return {"at": request.at}


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
    return _route_or_503(lambda: orders.route_for(neighbor, mode))


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


@app.get("/api/orders")
def list_orders() -> list[EvacuationOrder]:
    """One evacuation order per zone with residents: proposed, or approved by the coordinator."""
    return orders.orders()


@app.post("/api/orders/{zone}")
def approve_order(zone: str, decision: OrderDecision) -> EvacuationOrder:
    """The coordinator approves or changes a zone's order; the agent reads it from then on."""
    order = orders.approve(zone, decision)
    if order is None:
        raise HTTPException(status_code=404, detail=f"Unknown zone {zone} or destination {decision.destination_id}")
    return order


@app.get("/api/safe-points")
def list_safe_points() -> list[SafePoint]:
    """Candidate destinations, and whether each is safe at the scenario time."""
    return orders.safe_point_list()


@app.get("/api/fire-area")
def fire_area(crew: bool = False) -> dict:
    """The area routes avoid at the scenario time: residents' routes, or crews' with `crew=true`."""
    return evacuation.fire_area(crew=crew)


class TextTriageRequest(BaseModel):
    neighbor_id: str
    text: str = Field(min_length=1, max_length=1000, description="What the resident said, typed in")


@app.get("/api/triage/text")
def text_triage_available() -> dict:
    """Whether typed answers can be classified (an LLM is configured)."""
    return {"available": text_triage.available()}


@app.post("/api/triage/text")
def triage_from_text(request: TextTriageRequest, background: BackgroundTasks) -> dict:
    """The last resort when voice fails: classify a typed answer and record it like a call would."""
    if state.get(request.neighbor_id) is None:
        raise HTTPException(status_code=404, detail=f"Unknown neighbor {request.neighbor_id}")
    try:
        report, classification = text_triage.report_from_text(request.neighbor_id, request.text)
    except text_triage.ClassifierUnavailable as error:
        raise HTTPException(status_code=503, detail="The classifier is unavailable; use the buttons") from error
    neighbor = report_status(report, background)
    return {"neighbor": neighbor.model_dump(mode="json"), "classification": classification.model_dump(mode="json")}


@app.post("/api/reset")
def reset() -> dict:
    """Reload the registry and forget the replay moment, orders and alerts. Restarts the demo."""
    state.load()
    state.replay_time = None
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
        summary=_with_order(request.zone, _fire_summary(request.zone, minutes)),
    )


def _with_order(zone: str, summary: str) -> str:
    """Append the coordinator's approved order for the zone, the one thing every resident must hear."""
    order = orders.approved_order(zone)
    return f"{summary} {order.message}" if order else summary


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


def _route_or_503(plan) -> Route:
    try:
        return plan()
    except evacuation.RoutingUnavailable as error:
        raise HTTPException(status_code=503, detail="Routing is unavailable right now") from error


@app.post("/tools/get_evacuation_route")
def get_evacuation_route(request: EvacuationRouteRequest) -> Route:
    """Route from a registered resident's home to the nearest safe point the fire is not heading for."""
    neighbor = state.find_by_address(request.address)
    if neighbor is None:
        raise HTTPException(status_code=404, detail=f"Address not in the registry: {request.address}")
    return _route_or_503(lambda: orders.route_for(neighbor, request.mode))


logger = logging.getLogger("hackfire")


def _text_the_crew(rescue_id: str, message: str) -> None:
    """Runs after the response, so the voice agent never waits on Twilio. A failure is logged and
    the alert stays on the dashboard, marked as not sent."""
    try:
        sms.send(settings.crew_phone, message)
    except httpx.HTTPError:
        logger.exception("crew SMS for %s failed", rescue_id)
        return
    state.mark_alert_sent(rescue_id)


@app.post("/tools/report_status")
def report_status(request: ReportStatusRequest, background: BackgroundTasks) -> Neighbor:
    alerts_before = len(state.alerts())
    neighbor = state.report(request)
    if neighbor is None:
        raise HTTPException(status_code=404, detail=f"Unknown neighbor {request.neighbor_id}")
    # A new rescue became a crew alert (state.py): text it to the crew when Twilio is set up.
    if len(state.alerts()) > alerts_before and sms.configured() and settings.crew_phone:
        alert = state.alerts()[0]
        background.add_task(_text_the_crew, alert.rescue_id, alert.message)
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

    # The tile cache's service worker must be served from the root to control the whole page.
    @app.get("/tile-cache-sw.js", include_in_schema=False)
    def tile_cache_worker() -> FileResponse:
        return FileResponse(dashboard_dir / "tile-cache-sw.js", media_type="text/javascript")
