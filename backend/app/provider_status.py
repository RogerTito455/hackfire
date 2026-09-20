"""Whether each external service answers: up, degraded, down, configured (set up, never called
here) or not configured, with a short reason in the dashboard's language.

Checks run in parallel in a small thread pool, each with a short HTTP timeout, and the answer waits
for them at most WAIT_S: a check still running by then keeps its last result (or says it has not
answered yet) and stores its own when it finishes. Results are cached for TTL_S; openrouteservice's
for longer, because its check is a real route and counts against the daily quota while there is quota
left. The HTTP calls themselves live in providers/. See docs/setup/operations.md.
"""

import threading
import time
from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor, wait
from dataclasses import dataclass, field
from datetime import UTC, datetime

import httpx

from .config import settings
from .i18n import t
from .models import ProviderState, ProviderStatus
from .providers import deepfire, dgt, overpass, routing, sms, voice, vonage

TIMEOUT_S = 4.0
WAIT_S = 5.0
TTL_S = 60.0
ORS_TTL_S = 15 * 60.0


@dataclass(frozen=True)
class Check:
    state: ProviderState
    reason: str  # a key under "providers" in app/locales
    values: dict = field(default_factory=dict)


@dataclass(frozen=True)
class Provider:
    id: str
    name: str  # a brand name: not translated
    probe: Callable[[httpx.Client], Check]
    ttl_s: float = TTL_S
    # An optional service disappears from the panel while it is not configured: a coordinator needs
    # to see what the demo runs on, not a list of what nobody set up. The SMS providers are the
    # optional ones; the fallback is on screen anyway ("crew alerts stay on the dashboard").
    optional: bool = False


def _client() -> httpx.Client:
    return httpx.Client(timeout=TIMEOUT_S)


def _failure(error: Exception) -> Check:
    if isinstance(error, httpx.TimeoutException):
        return Check(ProviderState.DOWN, "timeout", {"seconds": int(TIMEOUT_S)})
    return Check(ProviderState.DOWN, "unreachable")


def _by_code(code: int) -> Check:
    if 200 <= code < 300:
        return Check(ProviderState.UP, "ok")
    if code in (401, 403):
        return Check(ProviderState.DOWN, "rejected", {"code": code})
    if code in (429, 502, 503, 504):
        return Check(ProviderState.DEGRADED, "busy", {"code": code})
    return Check(ProviderState.DOWN, "http", {"code": code})


def check_deepfire(client: httpx.Client) -> Check:
    if not deepfire.configured():
        return Check(ProviderState.NOT_CONFIGURED, "deepfireOff")
    try:
        code = deepfire.ping(client)
    except httpx.HTTPStatusError as error:
        code = error.response.status_code
    except httpx.HTTPError as error:
        return _failure(error)
    result = _by_code(code)
    if result.state == ProviderState.DEGRADED:
        return Check(ProviderState.DEGRADED, "deepfireBusy", {"code": code})
    return result


def check_routing(client: httpx.Client) -> Check:
    if not routing.configured():
        return Check(ProviderState.NOT_CONFIGURED, "orsOff")
    try:
        code, body = routing.ping(client)
    except httpx.HTTPError as error:
        failure = _failure(error)
        return Check(ProviderState.DEGRADED, "orsDown", failure.values)
    if code == 403 and "quota" in body.lower():
        return Check(ProviderState.DEGRADED, "orsQuota")
    if code == 429:
        return Check(ProviderState.DEGRADED, "orsRate")
    if code == 403 or code == 401:
        return Check(ProviderState.DOWN, "rejected", {"code": code})
    # 2010 is "no routable point near here": openrouteservice answered and took the key, which is
    # what this check is for. It must never read as an outage on the status panel.
    if code == 404 and '"code":2010' in body.replace(" ", ""):
        return Check(ProviderState.UP, "ok")
    return _by_code(code)


def check_overpass(client: httpx.Client) -> Check:
    servers = overpass.servers()

    def answers(url: str) -> bool:
        try:
            return 200 <= overpass.ping(client, url) < 300
        except httpx.HTTPError:
            return False

    with ThreadPoolExecutor(max_workers=len(servers)) as pool:
        up = sum(pool.map(answers, servers))
    if up == len(servers):
        return Check(ProviderState.UP, "overpassAll", {"count": up})
    if up:
        return Check(ProviderState.DEGRADED, "overpassSome", {"up": up, "count": len(servers)})
    return Check(ProviderState.DOWN, "overpassNone")


def check_slng(client: httpx.Client) -> Check:
    if not voice.web_sessions_configured():
        return Check(ProviderState.NOT_CONFIGURED, "slngOff")
    try:
        code = voice.ping(client)
    except httpx.HTTPError as error:
        return _failure(error)
    if code == 404:
        return Check(ProviderState.DEGRADED, "slngNoAgent")
    return _by_code(code)


def check_twilio(_client: httpx.Client) -> Check:
    """Configured or not: checking would mean sending a message."""
    if not sms.configured():
        return Check(ProviderState.NOT_CONFIGURED, "twilioOff")
    if not settings.crew_phone:
        return Check(ProviderState.NOT_CONFIGURED, "twilioNoCrew")
    return Check(ProviderState.CONFIGURED, "twilioOn")


def check_vonage(_client: httpx.Client) -> Check:
    """Configured or not: checking would mean sending a message."""
    if not vonage.video_configured():
        return Check(ProviderState.NOT_CONFIGURED, "vonageOff")
    return Check(ProviderState.CONFIGURED, "vonageOn" if vonage.sms_configured() else "vonageVideoOnly")


def check_dgt(client: httpx.Client) -> Check:
    """The DGT's public DATEX II feed: no key, so up or down."""
    try:
        code = dgt.ping(client)
    except httpx.HTTPError as error:
        return _failure(error)
    return _by_code(code)


PROVIDERS: list[Provider] = [
    Provider("deepfire", "Deepfire", check_deepfire),
    Provider("openrouteservice", "openrouteservice", check_routing, ORS_TTL_S),
    Provider("overpass", "Overpass (OpenStreetMap)", check_overpass),
    Provider("slng", "SLNG", check_slng),
    Provider("twilio", "Twilio SMS", check_twilio, optional=True),
    Provider("vonage", "Vonage SMS", check_vonage, optional=True),
    Provider("dgt", "DGT", check_dgt),
]


@dataclass
class _Result:
    check: Check
    checked_at: datetime
    monotonic: float


_results: dict[str, _Result] = {}
_inflight: dict[str, Future] = {}
_lock = threading.RLock()  # a done callback can run inline, under the lock
_pool = ThreadPoolExecutor(max_workers=8, thread_name_prefix="provider-status")


def _run(provider: Provider) -> Check:
    try:
        with _client() as client:
            return provider.probe(client)
    except Exception as error:  # a check never takes the page down
        return _failure(error)


def _store(provider_id: str, future: Future) -> None:
    check = future.result()
    with _lock:
        _results[provider_id] = _Result(check, datetime.now(UTC), time.monotonic())
        _inflight.pop(provider_id, None)


def statuses(providers: list[Provider] | None = None, wait_s: float = WAIT_S) -> list[ProviderStatus]:
    """Every provider's status, checking again the ones older than their TTL."""
    providers = PROVIDERS if providers is None else providers
    now = time.monotonic()
    pending: list[tuple[str, Future]] = []
    with _lock:
        for provider in providers:
            cached = _results.get(provider.id)
            if cached is not None and now - cached.monotonic < provider.ttl_s:
                continue
            future = _inflight.get(provider.id)
            if future is None:
                future = _pool.submit(_run, provider)
                _inflight[provider.id] = future
                future.add_done_callback(lambda done, pid=provider.id: _store(pid, done))
            pending.append((provider.id, future))
    if pending:
        wait([future for _, future in pending], timeout=wait_s)
        # A finished check's callback may not have run yet: store it here too (the same result).
        for provider_id, future in pending:
            if future.done():
                _store(provider_id, future)
    answer = []
    with _lock:
        for provider in providers:
            result = _results.get(provider.id)
            if provider.optional and result is not None and result.check.state == ProviderState.NOT_CONFIGURED:
                continue
            if result is None:
                check, checked_at = Check(ProviderState.DEGRADED, "checking", {"seconds": int(wait_s)}), None
            else:
                check, checked_at = result.check, result.checked_at
            answer.append(
                ProviderStatus(
                    id=provider.id,
                    name=provider.name,
                    state=check.state,
                    reason=t(f"providers.{check.reason}", **check.values),
                    checked_at=checked_at,
                )
            )
    return answer


def forget() -> None:
    """Drop the cached results (tests)."""
    with _lock:
        _results.clear()
        _inflight.clear()
