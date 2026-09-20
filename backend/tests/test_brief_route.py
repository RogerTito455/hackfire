"""What the agent says on the phone: the destination, one road and the time, and nothing else.

A caller packing the car cannot hold three clauses; the full directions stay for the dashboard.
"""

from app import evacuation

DIRECTIONS = {
    "mode": "car",
    "destination": "San Martín de Valdeiglesias",
    "roads": ["Carretera Toledo a Valladolid", "N-403", "Carretera de Ávila"],
    "distance_m": 6000,
    "duration_s": 540,
    "avoids": "ahead",
    "ahead_h": 1,
}


def test_the_brief_route_names_the_destination_one_road_and_the_time() -> None:
    brief = evacuation.say_brief(DIRECTIONS)

    assert "San Martín de Valdeiglesias" in brief
    assert "Carretera Toledo a Valladolid" in brief
    assert "minutes" in brief
    assert "N-403" not in brief, "one road is enough to start driving"
    assert "kilometre" not in brief, "the distance is noise on a call"
    assert brief.count(".") == 1, "one sentence"


def test_a_route_that_does_not_exist_says_so() -> None:
    assert evacuation.say_brief({"none": True}) == evacuation.say({"none": True})
