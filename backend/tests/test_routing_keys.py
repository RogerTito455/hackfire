"""openrouteservice key rotation: a spent key steps aside for the next one, and when every key is
spent the caller sees the same failure as with a single key. No network: a fake transport answers."""

from dataclasses import replace
from types import SimpleNamespace

import httpx
import pytest

from app import evacuation
from app.models import TravelMode
from app.providers import routing

START, END = (-4.4588, 40.3829), (-4.46516, 40.45515)
QUOTA = httpx.Response(403, json={"error": "Quota exceeded"})
DISALLOWED = httpx.Response(403, json={"error": "Access to this API has been disallowed"})
FEATURE = {
    "type": "Feature",
    "geometry": {"type": "LineString", "coordinates": [[-4.4588, 40.3829], [-4.46516, 40.45515]]},
    "properties": {"summary": {"distance": 100.0, "duration": 60.0}, "segments": [{"steps": []}]},
}


@pytest.fixture(autouse=True)
def three_keys(monkeypatch: pytest.MonkeyPatch):
    """Three keys and no memory of a spent one, whatever the machine's .env holds."""
    routing._spent.clear()
    monkeypatch.setattr(routing, "settings", replace(routing.settings, ors_api_keys=["first", "second", "third"]))
    yield
    routing._spent.clear()


def answering(*, refuse: dict[str, httpx.Response]) -> tuple[httpx.Client, list[str]]:
    """A client that answers each key with `refuse[key]`, or with a route, and the keys it was asked with."""
    asked: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        key = request.headers["Authorization"]
        asked.append(key)
        return refuse.get(key) or httpx.Response(200, json={"features": [FEATURE]})

    return httpx.Client(transport=httpx.MockTransport(handler)), asked


def ask(client: httpx.Client) -> dict:
    return routing.route_avoiding(client, START, END, TravelMode.CAR, None)


def test_a_key_whose_quota_is_spent_hands_over_to_the_next_one() -> None:
    client, asked = answering(refuse={"first": QUOTA})

    assert ask(client)["type"] == "Feature"

    assert asked == ["first", "second"]


def test_a_spent_key_is_not_tried_again_in_this_process() -> None:
    client, asked = answering(refuse={"first": QUOTA})

    ask(client)
    ask(client)

    assert asked == ["first", "second", "second"]


def test_a_rate_limited_key_hands_over_but_keeps_its_quota() -> None:
    client, asked = answering(refuse={"first": httpx.Response(429)})

    assert ask(client)["type"] == "Feature"

    # 40 a minute is a pause, not an allowance that is gone: the first key is tried again.
    assert asked == ["first", "second"]
    ask(client)
    assert asked[-2:] == ["first", "second"]


def test_another_refusal_stays_with_the_key_that_got_it() -> None:
    client, asked = answering(refuse={"first": DISALLOWED})

    with pytest.raises(httpx.HTTPStatusError) as refusal:
        ask(client)

    assert refusal.value.response.status_code == 403
    assert asked == ["first"]


def test_no_route_between_the_points_is_not_a_key_problem() -> None:
    not_found = httpx.Response(404, json={"error": {"code": routing.ROUTE_NOT_FOUND, "message": "no route"}})
    client, asked = answering(refuse={"first": not_found})

    with pytest.raises(routing.NoRouteFound):
        ask(client)

    assert asked == ["first"]


def test_with_every_key_spent_the_caller_sees_what_it_saw_with_one() -> None:
    client, asked = answering(refuse={"first": QUOTA, "second": QUOTA, "third": QUOTA})

    with pytest.raises(httpx.HTTPStatusError) as refusal:
        ask(client)

    assert refusal.value.response.status_code == 403
    assert asked == ["first", "second", "third"]
    # Nothing is left to try, so the last key answers again: asking with a spent key costs no quota,
    # and openrouteservice's own 403 is what `evacuation.plan` turns into RoutingUnavailable.
    with pytest.raises(httpx.HTTPStatusError):
        ask(client)
    assert asked[-1] == "third"


def test_the_planner_still_reports_routing_unavailable_when_every_key_is_spent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, _ = answering(refuse={"first": QUOTA, "second": QUOTA, "third": QUOTA})
    monkeypatch.setattr(evacuation, "_disk_cache", lambda: {})
    monkeypatch.setattr(evacuation, "_memory", {})
    monkeypatch.setattr(evacuation, "httpx", SimpleNamespace(Client=lambda **_k: client, HTTPError=httpx.HTTPError))

    with pytest.raises(evacuation.RoutingUnavailable):
        evacuation.plan(START, END, TravelMode.CAR, "Cebreros", evacuation.current().scenario_time)


def test_no_key_configured_is_still_one_attempt(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(routing, "settings", replace(routing.settings, ors_api_keys=[]))
    client, asked = answering(refuse={"": httpx.Response(403, json={"error": "Authorization field missing"})})

    with pytest.raises(httpx.HTTPStatusError):
        ask(client)

    assert asked == [""] and not routing.configured()
