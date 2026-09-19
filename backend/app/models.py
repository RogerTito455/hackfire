from datetime import datetime
from enum import StrEnum

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


class EvacuationRouteRequest(BaseModel):
    address: str
    mode: TravelMode = TravelMode.CAR


class Route(BaseModel):
    mode: TravelMode
    distance_m: float | None = None
    duration_s: float | None = None
    spoken_directions: str
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
