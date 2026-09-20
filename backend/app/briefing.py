"""What the voice agents are told: the fire and the coordinator's order, and a resident's call data.

The get_fire_status tool answers with fire_summary, and every call to a resident starts with
call_variables, so the resident agent opens with the order instead of looking it up while the
resident waits.
"""

import logging

from . import evacuation, i18n, impact, orders
from .config import settings
from .i18n import t
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
    # In the agents' language, whoever starts the call: the dashboard's own language must not leak in.
    with i18n.using(settings.agent_locale):
        return {
            "neighbor_id": neighbor.id,
            "resident_name": neighbor.name,
            "address": neighbor.address,
            "zone": neighbor.zone,
            "fire_status": fire_summary(neighbor.zone, state.minutes_to_impact(neighbor.zone)),
            "route": _route_by_car(neighbor),
        }


def crew_briefing(neighbor: Neighbor) -> str:
    """One sentence for the crew's phone: who needs help, where, how many and how long there is.

    It travels with the call, so the agent says it in its first breath instead of waiting to be
    asked; its tools still answer everything after that.
    """
    with i18n.using(settings.crew_locale):
        minutes = state.minutes_to_impact(neighbor.zone)
        return t(
            "crew.briefing",
            name=neighbor.name,
            address=neighbor.address,
            people=t("crew.people", count=neighbor.people) if neighbor.people else t("crew.peopleUnknown"),
            mobility=neighbor.mobility or t("crew.mobilityUnknown"),
            fire=t("crew.fireIn", count=round(minutes / 60)) if minutes else t("crew.fireUnknown"),
        )


def crew_call_data(neighbor: Neighbor) -> dict[str, str]:
    """What the crew's call carries: the rescue in one sentence and the way in, both said up front."""
    with i18n.using(settings.crew_locale):
        try:
            route = evacuation.rescue_route(neighbor)
            way_in = route.brief or route.spoken_directions
        except Exception:  # a call must go out even when routing does not answer
            logger.exception("no crew route for the call about %s", neighbor.id)
            way_in = t("route.unknown")
    return {"rescue": crew_briefing(neighbor), "route": way_in}


def _route_by_car(neighbor: Neighbor) -> str:
    try:
        route = orders.route_for(neighbor, TravelMode.CAR)
        # What the agent says on the phone is the short version; the dashboard keeps the full one.
        directions = route.brief or route.spoken_directions
    except Exception:
        # A call must start even when routing fails; the agent can still ask for a route.
        logger.exception("no route by car for %s at call start", neighbor.id)
        return ""
    # route_for leads with the order, which fire_status already carries.
    order = orders.approved_order(neighbor.zone)
    return directions.removeprefix(order.message).strip() if order else directions


def _spoken_span(minutes: int) -> tuple[str, int]:
    """("minutes", 25) or ("hours", 3), rounded down: a lead time is never overstated to a resident."""
    if minutes < 90:
        return "Minutes", max(5, 5 * (minutes // 5))
    return "Hours", minutes // 60


def _fire_line(zone: str, minutes: int | None) -> str:
    name = impact.zone_name(zone)
    if minutes is None:
        horizon = impact.remaining_horizon_minutes(state.clock())
        if horizon is None:
            return t("fire.noForecast", zone=name)
        unit, count = _spoken_span(horizon)
        return t(f"fire.noImpact{unit}", zone=name, count=count)
    if minutes == 0:
        return t("fire.covered", zone=name)
    unit, count = _spoken_span(minutes)
    return t(f"fire.reaches{unit}", zone=name, count=count)
