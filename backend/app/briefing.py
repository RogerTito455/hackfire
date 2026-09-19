"""What the resident agent is told about a zone: the fire and the coordinator's order.

The get_fire_status tool answers with it, and a call starts with it (campaign.call_variables), so
the agent can open with the order instead of looking it up while the resident waits.
"""

from . import impact, orders
from .state import state


def fire_summary(zone: str) -> str:
    """The fire at the replay moment, then the zone's approved order, if any: one line to say."""
    summary = _fire_line(zone, state.minutes_to_impact(zone))
    order = orders.approved_order(zone)
    return f"{summary} {order.message}" if order else summary


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
