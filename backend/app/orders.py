"""Evacuation orders per zone, the way civil protection gives them.

The authority orders a whole zone at once ("everyone in La Atalaya: leave for San Martín"), so the
message is the same for every neighbour and arrivals can be counted. Here the system proposes one
order per zone in the registry (the nearest safe point the forecast does not reach, measured from
the zone's centre, or sheltering in place when there is none) and the coordinator approves or
changes it. Only approved orders reach the agent: `get_fire_status` reads the order out and
`get_evacuation_route` leads each resident to that destination. See
docs/findings/2026-09-19-evacuation-destinations.md.
"""

from datetime import datetime

from shapely.geometry import shape

from . import closures, evacuation, geo, impact
from .scenario import current
from .i18n import t
from .models import (
    EvacuationOrder,
    Neighbor,
    OrderAction,
    OrderDecision,
    Route,
    SafePoint,
    TravelMode,
    TriageStatus,
)
from .state import state


def _centre(zone_id: str) -> tuple[float, float]:
    zone = impact.zones().get(zone_id)
    if zone is not None:
        point = zone.geometry.centroid
        return point.x, point.y
    residents = [n for n in state.neighbors() if n.zone == zone_id]
    return (
        sum(n.lon for n in residents) / len(residents),
        sum(n.lat for n in residents) / len(residents),
    )


def _proposal(zone_id: str, at: datetime) -> tuple[OrderAction, evacuation.Place | None]:
    candidates = evacuation.safe_points(at)
    if not candidates:
        return OrderAction.SHELTER, None
    centre = _centre(zone_id)
    here = evacuation.geo.point_m(*centre)
    nearest = min(candidates, key=lambda p: here.distance(evacuation.geo.point_m(p.lon, p.lat)))
    return OrderAction.EVACUATE, nearest


def message(zone_name: str, action: OrderAction, destination: str | None) -> str:
    if action == OrderAction.EVACUATE and destination:
        return t("order.leave", zone=zone_name, destination=destination)
    return t("order.stay", zone=zone_name)


def _place(place_id: str | None) -> evacuation.Place | None:
    return next((p for p in evacuation.all_places() if p.id == place_id), None)


def orders(at: datetime | None = None) -> list[EvacuationOrder]:
    """One order per zone with residents in the registry, most urgent first."""
    at = at or current().scenario_time
    result = []
    for zone_id in sorted({n.zone for n in state.neighbors()}):
        proposed_action, proposed = _proposal(zone_id, at)
        decision = state.orders.get(zone_id)
        action = decision.action if decision else proposed_action
        destination = _place(decision.destination_id) if decision else proposed
        if action == OrderAction.SHELTER:
            destination = None
        name = impact.zone_name(zone_id)
        result.append(
            EvacuationOrder(
                zone=zone_id,
                zone_name=name,
                residents=sum(n.zone == zone_id for n in state.neighbors()),
                minutes_to_impact=impact.minutes_to_impact(zone_id, at),
                proposed_action=proposed_action,
                proposed_destination_id=proposed.id if proposed else None,
                action=action,
                destination_id=destination.id if destination else None,
                destination_name=destination.name if destination else None,
                approved=decision is not None,
                message=message(name, action, destination.name if destination else None),
            )
        )
    return sorted(result, key=lambda o: (o.minutes_to_impact is None, o.minutes_to_impact or 0, o.zone))


def approve(zone_id: str, decision: OrderDecision) -> EvacuationOrder | None:
    """Record the coordinator's order for a zone. None if the zone or destination is unknown."""
    if zone_id not in {n.zone for n in state.neighbors()}:
        return None
    if decision.action == OrderAction.EVACUATE and _place(decision.destination_id) is None:
        return None
    state.orders[zone_id] = decision
    return next(o for o in orders() if o.zone == zone_id)


def approved_order(zone_id: str) -> EvacuationOrder | None:
    if zone_id not in state.orders:
        return None
    return next((o for o in orders() if o.zone == zone_id), None)


def route_for(neighbor: Neighbor, mode: TravelMode) -> Route:
    """The resident's route under their zone's approved order, or to their own nearest safe point."""
    order = approved_order(neighbor.zone)
    if order is None:
        return evacuation.evacuation_route(neighbor, mode)
    if order.action == OrderAction.SHELTER:
        return Route(mode=mode, spoken_directions=order.message)
    destination = _place(order.destination_id)
    route = evacuation.route_to(neighbor, destination, mode)
    if route.geometry is None and closures.fingerprint():
        # A closed road cuts the ordered destination off: say so, and send them to the fastest one left.
        home = (neighbor.lon, neighbor.lat)
        at = current().scenario_time
        others = evacuation.nearest_safe_points(at, home, exclude=destination.id)
        detour = evacuation.fastest_reachable(home, others, mode, at)
        if detour is not None:
            closed = t("route.closed", destination=destination.name)
            return detour.model_copy(update={"spoken_directions": f"{order.message} {closed} {detour.spoken_directions}"})
    return route.model_copy(update={"spoken_directions": f"{order.message} {route.spoken_directions}"})


def safe_point_list(at: datetime | None = None) -> list[SafePoint]:
    at = at or current().scenario_time
    qualifying = {p.id for p in evacuation.safe_points(at)}
    return [SafePoint(id=p.id, name=p.name, lat=p.lat, lon=p.lon, safe=p.id in qualifying) for p in evacuation.all_places()]


def leaving_through(lon: float, lat: float, radius_m: float) -> list[str]:
    """Residents already evacuating whose route, as it stands, passes within `radius_m` of a point:
    the ones a new closure there leaves on a cut road, who need calling again with the new route."""
    closed = geo.point_m(lon, lat).buffer(radius_m)
    affected = []
    for neighbor in state.neighbors():
        if neighbor.status != TriageStatus.EVACUATING:
            continue
        try:
            route = route_for(neighbor, TravelMode.CAR)
        except evacuation.RoutingUnavailable:
            continue
        if route.geometry is not None and geo.to_metres(shape(route.geometry)).intersects(closed):
            affected.append(neighbor.id)
    return affected
