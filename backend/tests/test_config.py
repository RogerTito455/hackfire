import pytest

from app.config import Settings


def test_cors_origins_tolerate_spaces_and_trailing_slashes(monkeypatch: pytest.MonkeyPatch) -> None:
    # A URL copied from the browser bar ends in "/", and the browser's Origin header never does.
    monkeypatch.setenv("HACKFIRE_CORS_ORIGINS", "https://hackfire.up.railway.app/, http://localhost:5173 ,")

    assert Settings().cors_origins == ["https://hackfire.up.railway.app", "http://localhost:5173"]


def test_empty_cors_origins_fall_back_to_the_local_dashboard(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HACKFIRE_CORS_ORIGINS", "")

    assert Settings().cors_origins == ["http://localhost:5173"]
