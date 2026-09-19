"""What the voice agents are told: the fire and the coordinator's order, and a resident's call data.

The get_fire_status tool answers with fire_summary, and every call to a resident starts with
call_variables, so the resident agent opens with the order instead of looking it up while the
resident waits.
"""

import logging

from . import impact, orders
from .models import Neighbor, TravelMode
from .state import state

logger = logging.getLogger(__name__)


def fire_summary(zone: str, minutes: int | None) -> str:
    """The fire at the replay moment, then the zone's approved order, if any: one line to say.

    With an order and nothing predicted, only the order: "nothing is predicted" must not undercut
    "leave now" (the slider can sit on a quiet moment).
    """
    order = orders.approved_order(zone)
    if order is not None and minutes is None:
        return order.message
    summary = _fire_line(zone, minutes)
    return f"{summary} {order.message}" if order else summary


def call_variables(neighbor: Neighbor) -> dict[str, str]:
    """The resident agent's call variables (voice/resident/agent.yaml), for a call or a web session.

    Besides who and where: the fire and the order (fire_status) and the route by car under that
    order (route). An empty route leaves the agent to ask get_evacuation_route when it needs one.
    """
    return {
        "neighbor_id": neighbor.id,
        "resident_name": neighbor.name,
        "address": neighbor.address,
        "zone": neighbor.zone,
        "fire_status": fire_summary(neighbor.zone, state.minutes_to_impact(neighbor.zone)),
        "route": _route_by_car(neighbor),
    }


def _route_by_car(neighbor: Neighbor) -> str:
    try:
        directions = orders.route_for(neighbor, TravelMode.CAR).spoken_directions
    except Exception:
        # A call must start even when routing fails; the agent can still ask for a route.
        logger.exception("no route by car for %s at call start", neighbor.id)
        return ""
    # route_for leads with the order, which fire_status already carries.
    order = orders.approved_order(neighbor.zone)
    return directions.removeprefix(order.message).strip() if order else directions


def _spoken_span(minutes: int) -> str:
    """"25 minutes" or "3 hours", rounded down: a lead time is never overstated to a resident."""
    if minutes < 90:
        return f"{max(5, 5 * (minutes // 5))} minutes"
    hours = minutes // 60
    return f"{hours} hour" if hours == 1 else f"{hours} hours"


def _fire_line(zone: str, minutes: int | None) -> str:
    name = impact.zone_name(zone)
    if minutes is None:
        horizon = impact.remaining_horizon_minutes(state.clock())
        if horizon is None:
            return f"There is no forecast for this moment, so nothing is predicted for {name}."
        return f"No predicted impact on {name} in the next {_spoken_span(horizon)}."
    if minutes == 0:
        return f"The predicted fire area already covers {name}."
    return f"The fire is predicted to reach {name} in about {_spoken_span(minutes)}."
