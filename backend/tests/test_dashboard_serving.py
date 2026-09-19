"""The deployed backend serves the built frontend: the dashboard at /, the landing page at /about."""

from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.main import serve_dashboard


@pytest.fixture
def client(tmp_path: Path) -> TestClient:
    """A stand-in for frontend/dist with the files the Vite build writes."""
    (tmp_path / "assets").mkdir()
    (tmp_path / "assets" / "dashboard.js").write_text("console.log('dashboard')")
    (tmp_path / "index.html").write_text("<title>dashboard</title>")
    (tmp_path / "about.html").write_text("<title>landing</title>")
    (tmp_path / "favicon.svg").write_text("<svg/>")
    (tmp_path / "dashboard-phone.webp").write_bytes(b"RIFF0000WEBP")
    (tmp_path / "tile-cache-sw.js").write_text("self.addEventListener('fetch', () => {})")
    app = FastAPI()
    serve_dashboard(app, tmp_path)
    return TestClient(app)


def test_the_dashboard_stays_at_the_root(client: TestClient) -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert "dashboard" in response.text


def test_the_landing_page_is_at_about(client: TestClient) -> None:
    response = client.get("/about")
    assert response.status_code == 200
    assert "landing" in response.text


def test_the_landing_page_picture_and_the_built_assets_are_served(client: TestClient) -> None:
    picture = client.get("/dashboard-phone.webp")
    assert picture.status_code == 200
    assert picture.headers["content-type"] == "image/webp"
    assert client.get("/assets/dashboard.js").status_code == 200
    assert client.get("/favicon.svg").status_code == 200


def test_other_paths_are_not_swallowed_by_the_frontend(client: TestClient) -> None:
    assert client.get("/about/anything").status_code == 404
    assert client.get("/api/unknown").status_code == 404
