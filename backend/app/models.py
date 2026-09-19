from datetime import datetime
from enum import StrEnum

from pydantic import AwareDatetime, BaseModel, Field


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
