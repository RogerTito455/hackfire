"""The fire crews' plan: which crew goes to which rescue, in what order, and whether it arrives in time.

It follows the rescue queue (most urgent first) and gives each rescue to the crew that is free first.
A crew drives from the fire station, spends ON_SCENE_MIN getting people into the vehicle, and drives
back before its next rescue. The margin is the predicted time to impact minus the arrival: the
coordinator sees at a glance which rescues the crews cannot reach before the fire.
"""

import math

from . import evacuation
from .models import CrewAssignment, CrewPlan, Neighbor, Verdict
from .state import state

ON_SCENE_MIN = 10
# Less margin than this, and a delay on the road means arriving with the fire.
TIGHT_MARGIN_MIN = 15


def drive_minutes(neighbor: Neighbor) -> int | None:
    """The crew's drive from the fire station to the resident, from the cached crew route."""
    try:
        route = evacuation.rescue_route(neighbor)
    except evacuation.RoutingUnavailable:
        return None
    return math.ceil(route.duration_s / 60) if route.duration_s is not None else None


def build(crews: int) -> CrewPlan:
    free_at = [0] * crews
    assignments = []
    for rescue in state.rescue_queue():
        crew = min(range(crews), key=lambda i: free_at[i])
        depart = free_at[crew]
        drive = drive_minutes(rescue.neighbor)
        eta = None if drive is None else depart + drive
        impact = rescue.minutes_to_impact
        margin = None if eta is None or impact is None else impact - eta
        assignments.append(
            CrewAssignment(
                rescue_id=rescue.rescue_id,
                neighbor_id=rescue.neighbor.id,
                name=rescue.neighbor.name,
                address=rescue.neighbor.address,
                people=rescue.neighbor.people,
                crew=crew + 1,
                depart_min=depart,
                drive_min=drive,
                eta_min=eta,
                minutes_to_impact=impact,
                margin_min=margin,
                verdict=_verdict(eta, margin),
            )
        )
        if drive is not None:
            free_at[crew] = depart + drive + ON_SCENE_MIN + drive
    return CrewPlan(crews=crews, on_scene_min=ON_SCENE_MIN, assignments=assignments)


def _verdict(eta: int | None, margin: int | None) -> Verdict:
    if eta is None:
        return "no_route"
    if margin is None or margin >= TIGHT_MARGIN_MIN:
        return "in_time"
    return "tight" if margin >= 0 else "late"
