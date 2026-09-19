from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


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
