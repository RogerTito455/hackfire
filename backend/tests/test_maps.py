"""The navigation link the crew gets by SMS: our route, not whatever the phone would pick."""

from app import maps

# A line that turns north halfway, as a route around a fire does.
ROUTE = [[-4.4976, 40.4154], [-4.4900, 40.4050], [-4.4800, 40.3950], [-4.4700, 40.3880], [-4.4603, 40.3831]]


def test_the_link_starts_and_ends_where_the_route_does() -> None:
    link = maps.navigate(ROUTE)

    assert link.startswith("https://www.google.com/maps/dir/?api=1")
    assert "origin=40.41540,-4.49760" in link
    assert "destination=40.38310,-4.46030" in link
    assert "travelmode=driving" in link


def test_the_middle_of_our_route_is_forced_as_waypoints() -> None:
    link = maps.navigate(ROUTE, waypoints=2)

    assert "waypoints=40.40500,-4.49000%7C40.38800,-4.47000" in link


def test_a_route_of_two_points_needs_no_waypoints() -> None:
    assert "waypoints" not in maps.navigate([[-4.49, 40.41], [-4.46, 40.38]])
