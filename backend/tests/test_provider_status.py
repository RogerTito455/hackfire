"""Provider status: each external service's state from fake HTTP answers, never the network. The ORS
403 of a spent daily quota reads as "quota spent", and a slow provider never holds up the others."""

import threading
import time
from dataclasses import replace

import httpx
import pytest
from fastapi.testclient import TestClient

from app import provider_status
from app.main import app
from app.models import ProviderState
from app.provider_status import Check, Provider
from app.providers import deepfire, overpass, routing, voice

client = TestClient(app)


@pytest.fixture(autouse=True)
def fresh(monkeypatch: pytest.MonkeyPatch):
    provider_status.forget()
    monkeypatch.setattr(deepfire, "_token", "token")
    yield
    provider_status.forget()


def answering(handler) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler))


def configured(monkeypatch: pytest.MonkeyPatch, **values) -> None:
    for module in (deepfire, routing, voice, provider_status):
        monkeypatch.setattr(module, "settings", replace(module.settings, **values))


def test_ors_403_quota_exceeded_is_quota_spent_using_the_cached_routes(monkeypatch: pytest.MonkeyPatch) -> None:
    configured(monkeypatch, ors_api_key="key")
    check = provider_status.check_routing(answering(lambda _r: httpx.Response(403, json={"error": "Quota exceeded"})))
    assert check.state == ProviderState.DEGRADED and check.reason == "orsQuota"
    monkeypatch.setattr(provider_status, "PROVIDERS", [Provider("openrouteservice", "openrouteservice", lambda _c: check)])
    english = client.get("/api/status/providers").json()[0]
    assert english["reason"] == "Quota spent: using the cached routes."
    provider_status.forget()
    spanish = client.get("/api/status/providers?lang=es").json()[0]
    assert spanish["reason"] == "Cuota agotada: se usan las rutas guardadas."


def test_ors_other_answers(monkeypatch: pytest.MonkeyPatch) -> None:
    configured(monkeypatch, ors_api_key="key")
    assert provider_status.check_routing(answering(lambda _r: httpx.Response(200, json={}))).state == ProviderState.UP
    denied = provider_status.check_routing(
        answering(lambda _r: httpx.Response(403, json={"error": "Access to this API has been disallowed"}))
    )
    assert (denied.state, denied.reason) == (ProviderState.DOWN, "rejected")
    assert provider_status.check_routing(answering(lambda _r: httpx.Response(429))).reason == "orsRate"
    configured(monkeypatch, ors_api_key="")
    assert provider_status.check_routing(answering(lambda _r: httpx.Response(200))).state == ProviderState.NOT_CONFIGURED


def test_deepfire_up_busy_and_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    configured(monkeypatch, deepfire_client_id="id", deepfire_client_secret="secret")
    assert provider_status.check_deepfire(answering(lambda _r: httpx.Response(200, json={}))).state == ProviderState.UP
    busy = provider_status.check_deepfire(answering(lambda _r: httpx.Response(503)))
    assert (busy.state, busy.reason) == (ProviderState.DEGRADED, "deepfireBusy")
    assert provider_status.check_deepfire(answering(lambda _r: httpx.Response(401))).state == ProviderState.DOWN


def test_a_timeout_is_down_with_the_seconds(monkeypatch: pytest.MonkeyPatch) -> None:
    configured(monkeypatch, slng_api_key="key")

    def slow(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("slow", request=request)

    check = provider_status.check_slng(answering(slow))
    assert (check.state, check.reason) == (ProviderState.DOWN, "timeout")
    assert check.values == {"seconds": int(provider_status.TIMEOUT_S)}


def test_slng_key_rejected_and_agent_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    configured(monkeypatch, slng_api_key="key")
    assert provider_status.check_slng(answering(lambda _r: httpx.Response(401))).reason == "rejected"
    assert provider_status.check_slng(answering(lambda _r: httpx.Response(404))).reason == "slngNoAgent"
    assert provider_status.check_slng(answering(lambda _r: httpx.Response(200, json={}))).state == ProviderState.UP


def test_overpass_counts_the_mirrors_that_answer(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(overpass, "servers", lambda: ["https://a.test/api/interpreter", "https://b.test/api/interpreter"])
    some = provider_status.check_overpass(
        answering(lambda request: httpx.Response(200 if request.url.host == "a.test" else 504))
    )
    assert (some.state, some.reason, some.values) == (ProviderState.DEGRADED, "overpassSome", {"up": 1, "count": 2})
    none = provider_status.check_overpass(answering(lambda _r: httpx.Response(429)))
    assert none.state == ProviderState.DOWN


def test_sms_providers_are_configured_or_not_and_never_called(monkeypatch: pytest.MonkeyPatch) -> None:
    def no_network(_request):
        raise AssertionError("no call")

    monkeypatch.setattr(provider_status.sms, "configured", lambda: True)
    configured(monkeypatch, crew_phone="+34000")
    assert provider_status.check_twilio(answering(no_network)).state == ProviderState.CONFIGURED
    monkeypatch.setattr(provider_status.vonage, "video_configured", lambda: False)
    assert provider_status.check_vonage(answering(no_network)).state == ProviderState.NOT_CONFIGURED


def test_a_slow_provider_does_not_hold_up_the_others() -> None:
    release = threading.Event()

    def slow(_client) -> Check:
        release.wait(5)
        return Check(ProviderState.UP, "ok")

    providers = [
        Provider("slow", "Slow", slow),
        Provider("fast", "Fast", lambda _c: Check(ProviderState.UP, "ok")),
    ]
    started = time.monotonic()
    answer = provider_status.statuses(providers, wait_s=0.3)
    assert time.monotonic() - started < 2
    by_id = {status.id: status for status in answer}
    assert by_id["fast"].state == ProviderState.UP and by_id["fast"].checked_at is not None
    assert by_id["slow"].state == ProviderState.DEGRADED and by_id["slow"].checked_at is None
    # The slow check finishes in the background and is served from then on.
    release.set()
    time.sleep(0.2)
    assert {s.id: s.state for s in provider_status.statuses(providers, wait_s=0.3)}["slow"] == ProviderState.UP


def test_results_are_cached_for_the_ttl() -> None:
    calls: list[int] = []

    def counted(_client) -> Check:
        calls.append(1)
        return Check(ProviderState.UP, "ok")

    providers = [Provider("counted", "Counted", counted, ttl_s=60)]
    provider_status.statuses(providers)
    provider_status.statuses(providers)
    assert len(calls) == 1


def test_a_check_that_raises_is_down_not_a_500() -> None:
    def broken(_client) -> Check:
        raise RuntimeError("boom")

    answer = provider_status.statuses([Provider("broken", "Broken", broken)])
    assert answer[0].state == ProviderState.DOWN


def test_the_endpoint_lists_every_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = [Provider(p.id, p.name, lambda _c: Check(ProviderState.UP, "ok"), p.ttl_s) for p in provider_status.PROVIDERS]
    monkeypatch.setattr(provider_status, "PROVIDERS", fake)
    body = client.get("/api/status/providers").json()
    assert [s["id"] for s in body] == ["deepfire", "openrouteservice", "overpass", "slng", "twilio", "vonage"]
    assert all(s["state"] == "up" and s["reason"] == "Answering." for s in body)
