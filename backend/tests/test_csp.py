"""The Content-Security-Policy every response carries (docs/findings/2026-09-20-csp.md).

The dashboard is one page of hand-written markup and one bundle; nothing it needs comes from
another origin except the map tiles and the two call SDKs. The policy says exactly that, so an
injected string can never become an injected script.
"""

from dataclasses import replace
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app import main
from app.main import content_security_policy, security_headers, serve_dashboard

HEADER = "content-security-policy"


@pytest.fixture
def client(tmp_path: Path) -> TestClient:
    """The deployed shape: the middleware in front of the built frontend."""
    (tmp_path / "assets").mkdir()
    (tmp_path / "assets" / "dashboard.js").write_text("console.log('dashboard')")
    (tmp_path / "index.html").write_text("<title>dashboard</title>")
    (tmp_path / "about.html").write_text("<title>landing</title>")
    (tmp_path / "favicon.svg").write_text("<svg/>")
    (tmp_path / "dashboard-phone.webp").write_bytes(b"RIFF0000WEBP")
    (tmp_path / "tile-cache-sw.js").write_text("self.addEventListener('fetch', () => {})")
    app = FastAPI()
    app.middleware("http")(security_headers)
    serve_dashboard(app, tmp_path)
    return TestClient(app)


@pytest.mark.parametrize("path", ["/", "/about", "/v/abc", "/crew/abc", "/assets/dashboard.js", "/tile-cache-sw.js"])
def test_every_page_and_asset_carries_the_policy(client: TestClient, path: str) -> None:
    """Including the service worker: a worker's policy comes from the headers of its own script."""
    response = client.get(path)
    assert response.status_code == 200
    assert response.headers[HEADER] == content_security_policy()


def test_nothing_runs_that_this_origin_did_not_serve() -> None:
    policy = content_security_policy()
    assert "default-src 'self'" in policy
    assert "script-src 'self'" in policy
    assert "style-src 'self' 'unsafe-inline'" in policy
    assert "object-src 'none'" in policy
    assert "base-uri 'self'" in policy
    assert "frame-ancestors 'none'" in policy
    # Only styles may be inline, for the video SDK's own elements (docs/findings/2026-09-20-csp.md).
    # Nothing may run: no inline script, no eval.
    directives = dict(part.split(" ", 1) for part in policy.split("; "))
    assert "'unsafe-inline'" not in directives["script-src"]
    assert "'unsafe-eval'" not in policy


def test_the_map_and_the_call_sdks_are_allowed_what_they_need() -> None:
    policy = content_security_policy()
    directives = dict(part.split(" ", 1) for part in policy.split("; "))
    # MapLibre GL builds its tile worker as a blob, and draws the basemap from OpenStreetMap.
    assert "blob:" in directives["worker-src"]
    assert "https://tile.openstreetmap.org" in directives["img-src"]
    # The service worker and the map both fetch the tiles themselves.
    assert "https://tile.openstreetmap.org" in directives["connect-src"]
    # LiveKit's room URL comes from SLNG per call, so only the scheme can be pinned.
    assert "wss:" in directives["connect-src"]
    # Vonage Video's signalling, media and configuration hosts.
    assert "https://*.opentok.com" in directives["connect-src"]
    assert "https://*.tokbox.com" in directives["connect-src"]
    # MapLibre's own stylesheet draws its controls from data: URLs.
    assert "data:" in directives["img-src"]


def test_a_deployment_can_add_the_origins_it_needs(monkeypatch: pytest.MonkeyPatch) -> None:
    """HACKFIRE_CSP_CONNECT, for a dashboard pointed at another backend or a Vonage region."""
    monkeypatch.setattr(main, "settings", replace(main.settings, csp_connect_origins=["https://api.example.org"]))
    assert "https://api.example.org" in content_security_policy()


def test_report_only_blocks_nothing(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """The escape hatch: the browser reports violations and lets everything through."""
    monkeypatch.setattr(main, "settings", replace(main.settings, csp_report_only=True))
    response = client.get("/")
    assert HEADER not in response.headers
    assert response.headers["content-security-policy-report-only"] == content_security_policy()


def test_the_voice_call_can_reach_livekit() -> None:
    """A browser call fetches the region list over https before it opens the wss room: 2026-09-20,
    a call with the policy on was refused `https://…livekit.cloud/settings/regions` without this."""
    policy = content_security_policy()
    connect = next(part for part in policy.split("; ") if part.startswith("connect-src"))
    assert "https://*.livekit.cloud" in connect
    assert "wss:" in connect
