"""Every key, URL and path the backend needs, read from the environment in one place."""

import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = REPO_ROOT / "data"

# Local keys live in the repo-root .env. Variables already set (tests, the host platform) win.
load_dotenv(REPO_ROOT / ".env")


def _env(name: str, default: str = "") -> str:
    """The variable, or the default when it is unset or empty (`.env.example` ships empty values)."""
    return os.environ.get(name, "").strip() or default


def _origins(name: str, default: str) -> list[str]:
    """Comma-separated origins, forgiving the spaces and trailing slashes of a pasted URL."""
    origins = [origin.strip().rstrip("/") for origin in _env(name).split(",")]
    return [origin for origin in origins if origin] or [default]


@dataclass(frozen=True)
class Settings:
    cors_origins: list[str] = field(
        default_factory=lambda: _origins("HACKFIRE_CORS_ORIGINS", "http://localhost:5173")
    )
    neighbors_file: str = field(default_factory=lambda: _env("HACKFIRE_NEIGHBORS_FILE"))
    # The built dashboard (frontend/dist). Set in the Dockerfile; empty locally, where Vite serves it.
    dashboard_dir: str = field(default_factory=lambda: _env("HACKFIRE_DASHBOARD_DIR"))
    crew_phone: str = field(default_factory=lambda: _env("HACKFIRE_CREW_PHONE"))
    # Where the dashboard is reachable, for the link in each crew alert.
    public_url: str = field(default_factory=lambda: _env("HACKFIRE_PUBLIC_URL", "http://localhost:5173").rstrip("/"))
    # The replay moment the calls happen at: routes avoid the fire burned up to then.
    # Default: 23 July 2026, 20:30 CEST, when the front was ~4 km from La Atalaya.
    scenario_time: datetime = field(
        default_factory=lambda: datetime.fromisoformat(_env("HACKFIRE_SCENARIO_TIME", "2026-07-23T18:30:00Z"))
    )

    deepfire_client_id: str = field(default_factory=lambda: _env("DEEPFIRE_CLIENT_ID"))
    deepfire_client_secret: str = field(default_factory=lambda: _env("DEEPFIRE_CLIENT_SECRET"))

    slng_api_key: str = field(default_factory=lambda: _env("SLNG_API_KEY"))
    slng_base_url: str = field(default_factory=lambda: _env("SLNG_BASE_URL"))

    nebius_api_key: str = field(default_factory=lambda: _env("NEBIUS_API_KEY"))
    nebius_base_url: str = field(default_factory=lambda: _env("NEBIUS_BASE_URL"))
    nebius_model: str = field(default_factory=lambda: _env("NEBIUS_MODEL"))

    ors_api_key: str = field(default_factory=lambda: _env("ORS_API_KEY"))

    # Public Overpass instances come and go; set OVERPASS_URL to another one if this refuses connections.
    overpass_url: str = field(
        default_factory=lambda: _env("OVERPASS_URL", "https://overpass-api.de/api/interpreter")
    )


settings = Settings()
