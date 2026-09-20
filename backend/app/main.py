import json
import logging
import time
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from pathlib import Path

import httpx
from fastapi import BackgroundTasks, FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import audit, autopilot, briefing, campaign, closures, crew_plan, crew_room, evacuation, i18n, impact, live, live_operations, live_spread, orders, provider_status, replay, rescue_video, scenario, text_triage
from .config import settings
# Live mode's official DGT road data and CAP alert drafts.
from . import cap, live_dgt
from .models import (
    AgentFocus,
    AuditEvent,
    Autopilot,
    AutopilotRequest,
    CampaignCall,
    CrewPlan,
    CrewRoom,
    RescueVideo,
    RescueVideoLink,
    VideoCapabilities,
    VideoAccess,
    VoiceCapabilities,
    WebSession,
    CrewAlert,
    EvacuationOrder,
    EvacuationRouteRequest,
    FireStatus,
    FireStatusRequest,
    Neighbor,
    OrderDecision,
    ProviderStatus,
    ReplayTimeRequest,
    ReportStatusRequest,
    Rescue,
    RescueRouteRequest,
    RoadClosure,
    RoadClosureRequest,
    Route,
    SafePoint,
    ScenarioInfo,
    TravelMode,
)
from .providers import sms, voice, vonage
from .state import crew_message, state

app = FastAPI(title="HackFire", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)


# --- Content-Security-Policy -------------------------------------------------
# What the dashboard's pages are allowed to load and talk to, so an injected string cannot become
# an injected script. Every response carries it, pages and assets alike: the tile cache's service
# worker takes its own policy from the headers of its script, so it needs the header too.
# Each source below is in the code, not a guess; docs/findings/2026-09-20-csp.md explains them.

# The basemap (OSM_STYLE in ui/TriageMap.tsx) and what public/tile-cache-sw.js caches for it.
TILE_HOST = "https://tile.openstreetmap.org"
# Vonage Video (#18, services/videoCall.ts): configuration and logging over https, signalling and
# media over wss. A project's own Rumor server is a subdomain of its own, so wildcards it is.
# video.api.vonage.com is where the SDK asks for the session before it connects: without it the
# crews' room fails with OT_CONNECT_FAILED (1006), seen in a browser on 20 September.
VONAGE_HOSTS = ("https://*.opentok.com", "https://*.tokbox.com", "https://video.api.vonage.com")
# LiveKit's client asks its cloud which region to use over https before it opens the wss room
# (verified 2026-09-20 with a browser call: without this the request is refused and the SDK falls
# back). SLNG hands out the deployment per call, so the subdomain is a wildcard.
LIVEKIT_HOSTS = ("https://*.livekit.cloud",)


def content_security_policy() -> str:
    """The policy every response carries. Extra connect sources come from the environment."""
    # LiveKit's room (services/voiceSession.ts) is a wss URL SLNG hands out per call, on whichever
    # deployment it picks, so the host cannot be listed ahead of time. `wss:` allows secure
    # WebSockets and nothing else; with script-src 'self' there is no script here to abuse it.
    connect = [
        "'self'",
        TILE_HOST,
        "wss:",
        *LIVEKIT_HOSTS,
        *VONAGE_HOSTS,
        settings.public_url,
        *settings.csp_connect_origins,
    ]
    return "; ".join(
        [
            "default-src 'self'",
            "base-uri 'self'",
            "object-src 'none'",
            "frame-ancestors 'none'",
            "form-action 'self'",
            "script-src 'self'",
            # MapLibre GL runs its tile worker from a blob URL it builds itself.
            "worker-src 'self' blob:",
            # The Vonage Video SDK sizes and places its own video elements with inline styles, and
            # refuses to show a stream without them (same browser test). Scripts stay on 'self', so
            # this allows styling, not code.
            "style-src 'self' 'unsafe-inline'",
            # data: for the arrows and badges in MapLibre's own stylesheet, blob: for the images
            # the map and the video SDKs build in memory.
            f"img-src 'self' data: blob: {TILE_HOST}",
            "font-src 'self'",
            # The agent's audio and a resident's video arrive as streams the browser attaches.
            "media-src 'self' blob:",
            "connect-src " + " ".join(dict.fromkeys(source for source in connect if source)),
        ]
    )


async def security_headers(request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
    """Stamp the Content-Security-Policy on every response: pages, assets and the API alike."""
    response = await call_next(request)
    header = "Content-Security-Policy-Report-Only" if settings.csp_report_only else "Content-Security-Policy"
    response.headers[header] = content_security_policy()
    return response


app.middleware("http")(security_headers)


@app.on_event("startup")
def warm_the_caches() -> None:
    """Read the cached files before the first request, not during it.

    On a live call the agent waits for the answer, and the first request after a deploy was paying
    for the 1.2 MB route cache, the hotspots and the forecasts all at once: 11.5 s of silence on the
    phone, measured on 20 September. Each loader caches itself, so this only moves the cost to boot.
    """
    try:
        evacuation._disk_cache()
        impact.zones()
        impact.forecasts()
        replay.burned_area_m(scenario.current().scenario_time)
    except Exception:  # a warm-up must never stop the service from starting
        logging.getLogger("hackfire").exception("warm-up failed; the first request will be slower")


@app.middleware("http")
async def request_locale(request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
    """The language of the sentences this request gets back (app/i18n.py).

    The agents' tools answer in HACKFIRE_AGENT_LOCALE; the dashboard gets ?lang= or its Accept-Language.
    """
    if request.url.path.startswith("/tools/"):
        locale = settings.agent_locale
    else:
        locale = request.query_params.get("lang") or i18n.negotiate(request.headers.get("accept-language"))
    token = i18n.set_current(locale)
    try:
        return await call_next(request)
    finally:
        i18n.reset(token)


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


@app.get("/api/scenario")
def get_scenario() -> ScenarioInfo:
    """The active scenario (HACKFIRE_SCENARIO): its name, the box the map fits, the replay window."""
    active = scenario.current()
    return ScenarioInfo(
        id=active.id,
        name=active.name,
        bbox=active.bbox,
        time_zone=active.time_zone,
        replay_start=active.replay_start,
        replay_end=active.replay_end,
        scenario_time=active.scenario_time,
        lead_time_zone=active.lead_time_zone,
    )


@app.get("/api/hotspots")
def list_hotspots() -> Response:
    """The active scenario's Deepfire hotspots (22–24 July 2026 for the demo), sorted by observed_at."""
    body = replay.hotspots_geojson()
    if body is None:
        raise HTTPException(status_code=404, detail="No cached hotspots: run pnpm data:hotspots")
    return Response(content=body, media_type="application/geo+json")


@app.get("/api/spread")
def get_spread() -> Response:
    """The scenario's predicted spread (23 July for the demo): one polygon per hour ahead, per forecast."""
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
    """The scenario's lead time (La Atalaya's for the demo) and how it was computed. Written by
    `pnpm data:lead-time`."""
    body = replay.lead_time_json()
    if body is None:
        raise HTTPException(status_code=404, detail="No cached lead time: run pnpm data:lead-time")
    return Response(content=body, media_type="application/json")


@app.post("/api/replay/time")
def set_replay_time(request: ReplayTimeRequest) -> dict:
    """The dashboard's slider moved: the agent's answers now refer to this replay moment."""
    state.replay_time = request.at
    # The demo autopilot, when on, sets the scripted residents and orders for this moment.
    before = state.snapshot() if autopilot.enabled() else None
    autopilot.follow(state.clock())
    if before is not None:
        audit.autopilot_changes(before, state.snapshot())
    return {"at": request.at}


@app.get("/api/autopilot")
def get_autopilot() -> Autopilot:
    """Whether the demo autopilot is on (autopilot.py), off by default. While it is on, its scripted
    outcomes on the replay clock and the recorded calls the dashboard shows with them."""
    return _autopilot()


def _autopilot() -> Autopilot:
    return Autopilot(enabled=autopilot.enabled(), calls=autopilot.calls(), transcripts=autopilot.used_transcripts())


@app.post("/api/autopilot")
def set_autopilot(request: AutopilotRequest) -> Autopilot:
    """Turn the demo autopilot on or off. On, it applies the script at `at` (or the replay clock) and
    follows the slider from then on; off, it puts back the state from before it was turned on. It never
    places a call or sends an SMS."""
    was_on, before = autopilot.enabled(), state.snapshot()
    if request.enabled:
        autopilot.turn_on(request.at or state.clock())
        if not was_on:
            audit.record("autopilot.on", actor="coordinator", source="dashboard")
        audit.autopilot_changes(before, state.snapshot())
    else:
        autopilot.turn_off()
        if was_on:
            audit.record("autopilot.off", actor="coordinator", source="dashboard")
    return _autopilot()


@app.get("/api/live/fires")
def list_live_fires() -> dict:
    """Deepfire's active fire clusters over Iberia, cached for a minute."""
    try:
        return live.active_fires()
    except live.LiveUnavailable as error:
        raise HTTPException(status_code=503, detail="Deepfire is unavailable right now") from error


@app.get("/api/live/spread")
def live_spread_runs() -> dict:
    """Predicted spread for the live fires: the latest completed Deepfire ELMFIRE run per fire, one
    cumulative polygon per hour. Cached for five minutes; the last good answer survives an outage."""
    try:
        return live_spread.predicted_spread()
    except live.LiveUnavailable as error:
        raise HTTPException(status_code=503, detail="Deepfire is unavailable right now") from error


@app.get("/api/live/operations/{fire_id}")
def live_fire_operations(fire_id: str) -> dict:
    """For one live fire with a Deepfire ELMFIRE run: the OpenStreetMap places its 12 h footprint
    reaches (plus a buffer), each one's time to impact, alert drafts that are never sent, and the roads
    to close to residents. A prediction, not an official warning. Places are fetched on demand for
    this fire only and cached per simulation."""
    try:
        return live_operations.operations(fire_id)
    except live.LiveUnavailable as error:
        raise HTTPException(status_code=503, detail="Deepfire is unavailable right now") from error
    except live_operations.NoSimulation as error:
        raise HTTPException(status_code=404, detail="No Deepfire spread simulation for this fire") from error
    except live_operations.PlacesUnavailable as error:
        raise HTTPException(status_code=503, detail="OpenStreetMap places are unavailable right now") from error


# --- Live mode: official DGT road data and CAP drafts ---------------------------------------------


@app.get("/api/live/dgt")
def live_dgt_incidents() -> dict:
    """Official data from the DGT (Spain's traffic authority), DATEX II on its National Access Point:
    the forest-fire incidents and the road or carriageway closures in force now. Cached for five
    minutes; the last good answer survives an outage (`stale: true`)."""
    try:
        return live_dgt.overview()
    except live_dgt.DgtUnavailable as error:
        raise HTTPException(status_code=503, detail="The DGT feed is unavailable right now") from error


@app.get("/api/live/operations/{fire_id}/cap")
def live_fire_cap(fire_id: str) -> Response:
    """The fire's alert drafts as one CAP 1.2 document (the format ES-Alert and EU-Alert systems take
    in), status Draft, one <info> per language. For Civil Protection to review; nothing is sent."""
    operations = live_fire_operations(fire_id)
    try:
        body = cap.document(operations)
    except ValueError as error:
        raise HTTPException(status_code=404, detail="No alert drafts for this fire") from error
    filename = f"hackfire-cap-draft-{''.join(c if c.isalnum() or c in '-_' else '_' for c in fire_id)}.xml"
    return Response(
        content=body,
        media_type="application/cap+xml",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# --- end of live DGT and CAP ---------------------------------------------------------------------


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


@app.get("/api/focus")
def get_focus() -> AgentFocus | None:
    """The rescue the voice agent last asked the route for, or null."""
    return state.focus


@app.get("/api/alerts")
def list_alerts() -> list[CrewAlert]:
    """Crew alerts for new rescues, newest first, written in the dashboard's language."""
    alerts = state.alerts()
    neighbors = {neighbor.id: neighbor for neighbor in state.neighbors()}
    return [
        alert.model_copy(update={"message": crew_message(neighbors[alert.neighbor_id], alert.link)})
        if alert.neighbor_id in neighbors
        else alert
        for alert in alerts
    ]


@app.get("/api/orders")
def list_orders() -> list[EvacuationOrder]:
    """One evacuation order per zone with residents: proposed, or approved by the coordinator."""
    return orders.orders()


@app.post("/api/orders/{zone}")
def approve_order(zone: str, decision: OrderDecision) -> EvacuationOrder:
    """The coordinator approves or changes a zone's order; the agent reads it from then on."""
    changed = zone in state.orders
    order = orders.approve(zone, decision)
    if order is None:
        raise HTTPException(status_code=404, detail=f"Unknown zone {zone} or destination {decision.destination_id}")
    audit.order_decided(order, changed=changed, actor="coordinator", source="dashboard")
    return order


@app.get("/api/voice")
def voice_capabilities() -> VoiceCapabilities:
    """What the dashboard can start: phone calls (a trunk is set up) and browser conversations."""
    return VoiceCapabilities(
        phone_calls=voice.phone_calls_configured(),
        web_sessions=voice.web_sessions_configured(),
        coordinator=voice.coordinator_configured(),
    )


@app.post("/api/neighbors/{neighbor_id}/web-session")
def start_web_session(neighbor_id: str) -> WebSession:
    """Take this resident's call in the browser: the campaign's call, for when no phone can ring.

    Like a campaign call, it needs the zone's order approved. Returns LiveKit's URL and a
    short-lived token for the browser; the SLNG key stays here.
    """
    resident = state.get(neighbor_id)
    if resident is None:
        raise HTTPException(status_code=404, detail=f"Unknown neighbor {neighbor_id}")
    if orders.approved_order(resident.zone) is None:
        raise HTTPException(status_code=409, detail=f"Approve the order for {resident.zone} before calling its residents")
    if not voice.web_sessions_configured():
        raise HTTPException(status_code=503, detail="The voice agent is not configured (SLNG_API_KEY)")
    try:
        session = voice.web_session(briefing.call_variables(resident), participant_name=resident.name)
    except voice.VoiceUnavailable as error:
        raise HTTPException(status_code=503, detail="The voice agent is unavailable right now") from error
    audit.record("call.webStarted", actor="coordinator", source="dashboard", subject=resident.id, name=resident.name)
    return session


# A browser call can end with the agent saying it recorded the outcome when it never called
# report_status (Galtea, docs/services/galtea.md). The resident must not stay "not called yet":
# a few seconds after the call ends, one still pending becomes no_answer, so the coordinator calls
# again. A report that lands in that time wins.
CALL_END_GRACE_S = 6.0


def _follow_up_if_unrecorded(neighbor_id: str, note: str) -> None:
    time.sleep(CALL_END_GRACE_S)
    if state.no_answer_if_pending(neighbor_id, observation=note):
        logger.info("call with %s ended without a report: marked no_answer for a follow-up call", neighbor_id)
        audit.status_reported(state.get(neighbor_id), source="safety_net", actor="system")


@app.post("/api/neighbors/{neighbor_id}/call-ended")
def browser_call_ended(neighbor_id: str, background: BackgroundTasks) -> dict:
    """The dashboard says a browser call with this resident has ended (the agent or the coordinator hung up)."""
    if state.get(neighbor_id) is None:
        raise HTTPException(status_code=404, detail=f"Unknown neighbor {neighbor_id}")
    audit.record("call.ended", actor="coordinator", source="dashboard", subject=neighbor_id, name=audit.resident_name(neighbor_id))
    background.add_task(_follow_up_if_unrecorded, neighbor_id, i18n.t("call.endedWithoutRecord"))
    return {"status": "checking"}


@app.post("/api/coordinator/web-session")
def start_coordinator_session() -> WebSession:
    """Ask the coordinator agent by voice from the dashboard (#10); the map follows its answers."""
    if not voice.coordinator_configured():
        raise HTTPException(status_code=503, detail="The coordinator agent is not configured (SLNG_API_KEY)")
    try:
        return voice.coordinator_web_session()
    except voice.VoiceUnavailable as error:
        raise HTTPException(status_code=503, detail="The coordinator agent is unavailable right now") from error


@app.get("/api/video")
def video_capabilities() -> VideoCapabilities:
    """Whether the dashboard can ask residents for live video, and text them the link (#18)."""
    return VideoCapabilities(video=vonage.video_configured(), sms=vonage.sms_configured())


@app.post("/api/rescues/{neighbor_id}/video")
def request_rescue_video(neighbor_id: str) -> RescueVideoLink:
    """Ask a resident who needs rescue for live video: a single-use link, texted when SMS works (#18)."""
    # The resident's link is texted to their real phone: not for a simulated rescue.
    if autopilot.enabled():
        raise HTTPException(status_code=409, detail="Turn off the call simulation before asking a resident for video")
    try:
        link = rescue_video.request(neighbor_id)
        audit.record(
            "video.linkTexted" if link.sms_sent else "video.linkShown",
            actor="coordinator",
            source="dashboard",
            subject=neighbor_id,
            name=audit.resident_name(neighbor_id),
        )
        return link
    except rescue_video.UnknownResident as error:
        raise HTTPException(status_code=404, detail=f"Unknown neighbor {neighbor_id}") from error
    except rescue_video.NotNeedsRescue as error:
        raise HTTPException(status_code=409, detail="Video is for residents who need rescue") from error
    except vonage.VonageUnavailable as error:
        raise HTTPException(status_code=503, detail="Live video is unavailable right now") from error


@app.get("/api/rescues/{neighbor_id}/video")
def watch_rescue_video(neighbor_id: str) -> RescueVideo:
    """The coordinator's dashboard polls this until the resident is on camera, then watches (#18)."""
    try:
        return rescue_video.watch(neighbor_id)
    except rescue_video.NoVideo as error:
        raise HTTPException(status_code=404, detail=f"No video was asked of {neighbor_id}") from error
    except vonage.VonageUnavailable as error:
        raise HTTPException(status_code=503, detail="Live video is unavailable right now") from error


@app.get("/api/video/{link_id}")
def join_rescue_video(link_id: str) -> VideoAccess:
    """The resident's page opens their camera with this; the link works once (#18)."""
    try:
        return rescue_video.join(link_id)
    except rescue_video.UnknownLink as error:
        raise HTTPException(status_code=404, detail="Unknown video link") from error
    except rescue_video.LinkUsed as error:
        raise HTTPException(status_code=410, detail="This video link was already used") from error
    except vonage.VonageUnavailable as error:
        raise HTTPException(status_code=503, detail="Live video is unavailable right now") from error


@app.post("/api/crew-room")
def open_crew_room() -> CrewRoom:
    """The command post opens the crews' room to share its map and voice; the link goes to the crews."""
    try:
        return crew_room.open_room()
    except vonage.VonageUnavailable as error:
        raise HTTPException(status_code=503, detail="Video is unavailable right now") from error


@app.get("/api/crew-room/{room_id}")
def join_crew_room(room_id: str) -> VideoAccess:
    """A crew's phone joins the room with the link it was sent."""
    try:
        return crew_room.join(room_id)
    except crew_room.UnknownRoom as error:
        raise HTTPException(status_code=404, detail="Unknown or closed room") from error
    except vonage.VonageUnavailable as error:
        raise HTTPException(status_code=503, detail="Video is unavailable right now") from error


@app.get("/api/crew-plan")
def get_crew_plan(crews: int | None = None) -> CrewPlan:
    """Which crew goes to which rescue, in order, and whether it gets there before the fire."""
    return crew_plan.build(max(1, min(crews or settings.crews, 10)))


@app.post("/api/campaigns/{zone}")
def start_campaign(zone: str, background: BackgroundTasks) -> list[CampaignCall]:
    """The coordinator starts the calls to a zone's residents, once its order is approved."""
    # The simulation approves orders, but real phones must never ring for a simulated workflow.
    if autopilot.enabled():
        raise HTTPException(status_code=409, detail="Turn off the call simulation before calling residents")
    try:
        calls = campaign.start(zone)
    except campaign.NoPhoneLine as error:
        raise HTTPException(status_code=503, detail="No phone line is set up: talk to each resident from the dashboard") from error
    except campaign.NotApproved as error:
        raise HTTPException(status_code=409, detail=f"Approve the order for {zone} before calling its residents") from error
    audit.record(
        "campaign.started",
        actor="coordinator",
        source="dashboard",
        subject=zone,
        zone=impact.zone_name(zone),
        count=sum(call.call_id is not None for call in calls),
        refused=sum(call.call_id is None for call in calls),
    )
    # One watcher for all of them: Starlette runs background tasks one after another.
    background.add_task(campaign.watch, calls)
    return calls


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
    neighbor = _record_report(report, background, source="typed_answer")
    return {"neighbor": neighbor.model_dump(mode="json"), "classification": classification.model_dump(mode="json")}


@app.get("/api/closures")
def list_closures() -> list[RoadClosure]:
    """Roads marked as cut, oldest first."""
    return closures.all()


@app.post("/api/closures")
def close_road(request: RoadClosureRequest) -> RoadClosure:
    """Mark a road as cut. Every route planned from now on goes around it. The answer names the
    residents already leaving by a route through it, for the coordinator to call again."""
    affected = orders.leaving_through(request.lon, request.lat, request.radius_m)
    closure = closures.add(request, affected)
    audit.record(
        "closure.added",
        actor="coordinator",
        source="dashboard",
        subject=closure.id,
        place=f"{closure.lat:.4f}, {closure.lon:.4f}",
        radius=round(closure.radius_m),
        count=len(affected),
    )
    return closure


@app.delete("/api/closures/{closure_id}", status_code=204)
def reopen_road(closure_id: str) -> Response:
    closure = next((c for c in closures.all() if c.id == closure_id), None)
    if closure is None or not closures.remove(closure_id):
        raise HTTPException(status_code=404, detail=f"Unknown closure {closure_id}")
    audit.record(
        "closure.removed", actor="coordinator", source="dashboard", subject=closure_id, place=f"{closure.lat:.4f}, {closure.lon:.4f}"
    )
    return Response(status_code=204)


@app.post("/api/reset")
def reset() -> dict:
    """Reload the registry and forget the replay moment, orders and alerts. Restarts the demo with
    the autopilot off."""
    autopilot.forget()
    state.load()
    state.replay_time = None
    campaign.forget()
    rescue_video.forget()
    crew_room.forget()
    closures.forget()
    # The audit file keeps everything; the log shown starts again from this event (app/audit.py).
    audit.record(audit.RESET, actor="coordinator", source="dashboard")
    return {"status": "reset", "neighbors": len(state.neighbors())}


# --- Audit log and provider status (docs/setup/operations.md) -------------------------------


def _audit_event(event: dict) -> AuditEvent:
    return AuditEvent(**event, message=audit.message(event))


@app.get("/api/audit")
def audit_log(limit: int = Query(default=15, ge=1, le=1000)) -> list[AuditEvent]:
    """The current run's decisions and outcomes, newest first, each as a sentence in the request's
    language. Never a phone number."""
    return [_audit_event(event) for event in audit.log.events(limit)]


@app.get("/api/audit/export")
def audit_export() -> Response:
    """The whole current run as a JSON file to download, newest first."""
    events = [_audit_event(event).model_dump(mode="json") for event in audit.log.events()]
    stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M")
    return Response(
        content=json.dumps(events, ensure_ascii=False, indent=2),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="hackfire-audit-{stamp}.json"'},
    )


@app.get("/api/status/providers")
def providers_status() -> list[ProviderStatus]:
    """Each external service: up, degraded, down, configured or not configured, with a reason.
    Checked in parallel with short timeouts and cached for about a minute."""
    return provider_status.statuses()


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
        summary=briefing.fire_summary(request.zone, minutes),
    )


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
    neighbor_id = rescue_id.removeprefix("rescue-")
    try:
        sms.send(settings.crew_phone, message)
    except httpx.HTTPError:
        logger.exception("crew SMS for %s failed", rescue_id)
        audit.record("alert.smsFailed", actor="system", subject=neighbor_id, name=audit.resident_name(neighbor_id))
        return
    state.mark_alert_sent(rescue_id)
    audit.record("alert.smsSent", actor="system", subject=neighbor_id, name=audit.resident_name(neighbor_id))


@app.post("/tools/report_status")
def report_status(
    request: ReportStatusRequest,
    background: BackgroundTasks,
    via: str | None = Query(default=None, description="dashboard: the coordinator's buttons, for the audit log"),
) -> Neighbor:
    return _record_report(request, background, source="manual_button" if via == "dashboard" else "agent_tool")


def _record_report(request: ReportStatusRequest, background: BackgroundTasks, source: str) -> Neighbor:
    alerts_before = len(state.alerts())
    neighbor = state.report(request)
    if neighbor is None:
        raise HTTPException(status_code=404, detail=f"Unknown neighbor {request.neighbor_id}")
    audit.status_reported(neighbor, source=source, actor="agent" if source == "agent_tool" else "coordinator")
    # A new rescue became a crew alert (state.py): text it to the crew when Twilio is set up.
    if len(state.alerts()) > alerts_before:
        alert = state.alerts()[0]
        texting = sms.configured() and bool(settings.crew_phone)
        audit.record(
            "alert.createdSms" if texting else "alert.createdDashboard",
            actor="system",
            source=source,
            subject=neighbor.id,
            name=neighbor.name,
        )
        if texting:
            background.add_task(_text_the_crew, alert.rescue_id, alert.message)
    return neighbor


@app.post("/tools/get_rescue_queue")
def get_rescue_queue() -> list[Rescue]:
    return state.rescue_queue()


@app.post("/tools/get_crew_plan")
def get_crew_plan_tool() -> CrewPlan:
    """For the coordinator agent: the crews' plan with the default number of crews."""
    return crew_plan.build(settings.crews)


@app.post("/tools/get_rescue_route")
def get_rescue_route(request: RescueRouteRequest) -> Route:
    rescue = next((r for r in state.rescue_queue() if r.rescue_id == request.rescue_id), None)
    if rescue is None:
        raise HTTPException(status_code=404, detail=f"Unknown rescue {request.rescue_id}")
    # The dashboard follows the agent: it draws the route the coordinator just asked for (#10).
    state.focus = AgentFocus(neighbor_id=rescue.neighbor.id, rescue_id=rescue.rescue_id, at=datetime.now(UTC))
    return _route_or_503(lambda: evacuation.rescue_route(rescue.neighbor))


# --- Dashboard ---------------------------------------------------------------
# Deployed, this process also serves the built dashboard, which then calls the API on its own
# origin. Only the dashboard's own paths: a catch-all mount at "/" would swallow the API's 404s
# and trailing-slash redirects. See docs/setup/deployment.md.


def serve_dashboard(target: FastAPI, dashboard_dir: Path) -> None:
    """Serve the built frontend: the dashboard at /, the landing page at /about, and their files."""
    target.mount("/assets", StaticFiles(directory=dashboard_dir / "assets"), name="dashboard-assets")

    @target.get("/", include_in_schema=False)
    def dashboard() -> FileResponse:
        return FileResponse(dashboard_dir / "index.html")

    # A resident's video link (#18) opens the same app, which shows the camera page for /v/<link>.
    @target.get("/v/{link_id}", include_in_schema=False)
    def resident_video_page(link_id: str) -> FileResponse:
        return FileResponse(dashboard_dir / "index.html")

    # A crew's link to the crews' room opens the same app too, on the room page.
    @target.get("/crew/{room_id}", include_in_schema=False)
    def crew_room_page(room_id: str) -> FileResponse:
        return FileResponse(dashboard_dir / "index.html")

    # The landing page for judges and visitors (frontend/about.html). The dashboard stays at /:
    # crew alert links, the runbook and the pitch all use the root URL.
    @target.get("/about", include_in_schema=False)
    def landing() -> FileResponse:
        return FileResponse(dashboard_dir / "about.html")

    # Vite copies frontend/public/ to the root of the build; each file there needs a route here.
    @target.get("/favicon.svg", include_in_schema=False)
    def favicon() -> FileResponse:
        return FileResponse(dashboard_dir / "favicon.svg")

    # The landing page's picture of the dashboard.
    @target.get("/dashboard-phone.webp", include_in_schema=False)
    def dashboard_picture() -> FileResponse:
        return FileResponse(dashboard_dir / "dashboard-phone.webp", media_type="image/webp")

    # The tile cache's service worker must be served from the root to control the whole page.
    @target.get("/tile-cache-sw.js", include_in_schema=False)
    def tile_cache_worker() -> FileResponse:
        return FileResponse(dashboard_dir / "tile-cache-sw.js", media_type="text/javascript")


if settings.dashboard_dir:
    serve_dashboard(app, Path(settings.dashboard_dir))
