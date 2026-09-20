from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import AwareDatetime, BaseModel, Field, field_validator


class TriageStatus(StrEnum):
    PENDING = "pending"
    EVACUATING = "evacuating"
    NO_ANSWER = "no_answer"
    NEEDS_RESCUE = "needs_rescue"


class TravelMode(StrEnum):
    CAR = "car"
    WALKING = "walking"


class Neighbor(BaseModel):
    id: str
    name: str
    # Never serialised: the dashboard URL is public and the registry holds real numbers.
    phone: str = Field(exclude=True)
    address: str
    zone: str
    lat: float
    lon: float
    status: TriageStatus = TriageStatus.PENDING
    people: int | None = None
    mobility: str | None = None
    observation: str | None = None
    updated_at: datetime | None = None


class FireStatusRequest(BaseModel):
    zone: str


class FireStatus(BaseModel):
    zone: str
    at_risk: bool
    minutes_to_impact: int | None = Field(
        default=None, description="Estimated minutes until the predicted fire reaches the zone"
    )
    summary: str
    stub: bool = False


class ReplayTimeRequest(BaseModel):
    at: AwareDatetime = Field(description="Replay moment the dashboard's slider is on")


class AutopilotTurn(BaseModel):
    speaker: Literal["agent", "resident"]
    text: str


class AutopilotTranscript(BaseModel):
    """A real call of the resident agent with a resident simulated by Galtea (data/demo_calls.json)."""

    scenario: str
    status: TriageStatus = Field(description="The last status the agent recorded with report_status")
    turns: list[AutopilotTurn]


class AutopilotCall(BaseModel):
    """A scripted outcome placed on the replay clock: when it lands, whose pin it sets, and the transcript
    shown next to it."""

    neighbor_id: str
    at: datetime
    status: TriageStatus
    transcript: str | None = Field(default=None, description="A key of `transcripts`")


class ScenarioInfo(BaseModel):
    """What the dashboard needs to know about the active scenario (app/scenario.py)."""

    id: str
    name: str
    bbox: tuple[float, float, float, float] = Field(description="min lon, min lat, max lon, max lat: the map fits it")
    time_zone: str = Field(description="IANA time zone the replay is told in")
    replay_start: datetime
    replay_end: datetime
    scenario_time: datetime = Field(description="The moment the calls happen at, and routes are planned for")
    lead_time_zone: str


class Autopilot(BaseModel):
    """The demo autopilot (autopilot.py): a labelled simulation of the workflow along the replay."""

    enabled: bool
    # While it is on: every scripted outcome for this registry, oldest first, and the transcripts they name.
    calls: list[AutopilotCall] = []
    transcripts: dict[str, AutopilotTranscript] = {}


class AutopilotRequest(BaseModel):
    enabled: bool
    at: AwareDatetime | None = Field(
        default=None, description="The slider's replay moment, to apply the script at before the slider next moves"
    )


class EvacuationRouteRequest(BaseModel):
    address: str
    mode: TravelMode = TravelMode.CAR


class Route(BaseModel):
    mode: TravelMode
    distance_m: float | None = None
    duration_s: float | None = None
    spoken_directions: str
    brief: str | None = Field(default=None, description="The same route in one sentence, for a phone call")
    geometry: dict | None = Field(default=None, description="GeoJSON LineString")
    stub: bool = False


class ReportStatusRequest(BaseModel):
    neighbor_id: str
    status: TriageStatus
    people: int | None = None
    mobility: str | None = None
    observation: str | None = None

    @field_validator("people", mode="before")
    @classmethod
    def _unreadable_count_is_unknown(cls, value: object) -> object:
        # SLNG passes the model's arguments through unchecked. A count in words must not reject
        # the call and lose the triage status with it.
        if isinstance(value, str) and not value.strip().isdigit():
            return None
        return value


class CampaignCall(BaseModel):
    """One resident's call in a campaign. Never carries the phone number."""

    neighbor_id: str
    call_id: str | None = Field(description="None when SLNG refused to place the call; the resident is then no_answer")


class RescueVideoLink(BaseModel):
    """The single-use link that opens a resident's camera (#18). Never carries the phone number."""

    neighbor_id: str
    link: str
    sms_sent: bool = Field(description="Whether the link was texted to the resident's registry phone")


class VideoAccess(BaseModel):
    """What a browser needs to join a resident's video: Vonage's application id, the session, a token."""

    application_id: str
    session_id: str
    token: str


class RescueVideo(BaseModel):
    """The coordinator's side of a resident's video: waiting for them, or a token to watch."""

    neighbor_id: str
    joined: bool = Field(description="Whether the resident has opened the link and turned on the camera")
    access: VideoAccess | None = Field(default=None, description="A subscriber token, once the resident has joined")


class CrewRoom(BaseModel):
    """The crews' room: the link the crews open, and the command post's token to share its screen."""

    link: str
    access: VideoAccess


class VideoCapabilities(BaseModel):
    video: bool = Field(description="Vonage is configured: the coordinator can ask a resident for live video")
    sms: bool = Field(description="The video link can be texted; otherwise the coordinator passes it on")


class VoiceCapabilities(BaseModel):
    phone_calls: bool = Field(description="An outbound trunk is set up, so the campaign can ring phones")
    web_sessions: bool = Field(description="The dashboard can take a resident's call in the browser")
    coordinator: bool = Field(description="The dashboard can talk to the coordinator agent in the browser")


class WebSession(BaseModel):
    """A browser conversation with the resident agent. Holds no SLNG key."""

    call_id: str
    livekit_url: str
    livekit_token: str
    max_session_seconds: int


Verdict = Literal["in_time", "tight", "late", "no_route"]


class CrewAssignment(BaseModel):
    """One rescue in the crews' plan. Minutes count from now."""

    rescue_id: str
    neighbor_id: str
    name: str
    address: str
    people: int | None
    crew: int = Field(description="Crew number, from 1")
    depart_min: int = Field(description="When the crew leaves the fire station")
    drive_min: int | None = Field(description="Drive from the fire station; None when no route is known")
    eta_min: int | None = Field(description="Arrival at the resident")
    minutes_to_impact: int | None = Field(description="Predicted minutes until the fire reaches the resident's zone")
    margin_min: int | None = Field(description="minutes_to_impact minus eta_min; negative means after the fire")
    verdict: Verdict


class RoadClosureRequest(BaseModel):
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    radius_m: float = Field(default=150, ge=30, le=1_000, description="How much of the road around the point is cut")
    note: str | None = Field(default=None, max_length=200)


class RoadClosure(RoadClosureRequest):
    """A road the coordinator marked as cut: no route goes through it, crews' included."""

    id: str
    created_at: AwareDatetime
    affected: list[str] = Field(
        default_factory=list,
        description="Residents already leaving by a route through here, who need the new one",
    )


class CrewPlan(BaseModel):
    crews: int
    on_scene_min: int = Field(description="Minutes a crew spends getting people into the vehicle")
    assignments: list[CrewAssignment]


class Rescue(BaseModel):
    rescue_id: str
    neighbor: Neighbor
    minutes_to_impact: int | None
    priority: int = Field(description="1 is the most urgent")


class RescueRouteRequest(BaseModel):
    rescue_id: str


class CrewAlert(BaseModel):
    """What the fire crew is told when a resident becomes needs_rescue."""

    rescue_id: str
    neighbor_id: str
    message: str
    link: str = Field(description="Opens the dashboard on this rescue with the crew's route drawn")
    created_at: datetime
    sent_by_sms: bool = Field(default=False, description="False: shown on the dashboard only")


class AgentFocus(BaseModel):
    """The rescue the voice agent last asked the route for, so the dashboard can draw it."""

    neighbor_id: str
    rescue_id: str
    at: datetime


class OrderAction(StrEnum):
    EVACUATE = "evacuate"
    SHELTER = "shelter"


class OrderDecision(BaseModel):
    """What the coordinator approves for a zone."""

    action: OrderAction
    destination_id: str | None = Field(default=None, description="A safe point id from data/places.json")


class EvacuationOrder(BaseModel):
    """One order per zone: proposed by the system, approved or changed by the coordinator."""

    zone: str
    zone_name: str
    residents: int
    minutes_to_impact: int | None
    proposed_action: OrderAction
    proposed_destination_id: str | None
    action: OrderAction
    destination_id: str | None
    destination_name: str | None
    approved: bool = False
    message: str = Field(description="What the agent tells everyone in the zone once approved")


class SafePoint(BaseModel):
    id: str
    name: str
    lat: float
    lon: float
    safe: bool = Field(description="Outside the forecast and at least 3 km from the fire at the scenario time")


class AuditEvent(BaseModel):
    """One decision or outcome in the audit log (app/audit.py). Never carries a phone number."""

    id: str
    at: AwareDatetime
    action: str = Field(description="The event's kind, such as order.approved or status.reported")
    actor: str = Field(description="coordinator, agent, autopilot or system")
    source: str | None = Field(default=None, description="Where a status came from: agent_tool, typed_answer, ...")
    subject: str | None = Field(default=None, description="A resident id, a zone id or a closure id")
    values: dict[str, str | int | float | bool | None] = Field(default_factory=dict)
    message: str = Field(description="The event as a sentence, in the request's language")


class ProviderState(StrEnum):
    UP = "up"
    DEGRADED = "degraded"
    DOWN = "down"
    CONFIGURED = "configured"  # set up; not checked, because checking would send something
    NOT_CONFIGURED = "not_configured"


class ProviderStatus(BaseModel):
    """Whether an external service answers (app/provider_status.py)."""

    id: str
    name: str
    state: ProviderState
    reason: str = Field(description="A short sentence in the request's language")
    checked_at: AwareDatetime | None = Field(default=None, description="None: the first check has not answered yet")
