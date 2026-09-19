"""Every key, URL and path the backend needs, read from the environment in one place."""

import os
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = REPO_ROOT / "data"


def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


@dataclass(frozen=True)
class Settings:
    cors_origins: list[str] = field(
        default_factory=lambda: _env("HACKFIRE_CORS_ORIGINS", "http://localhost:5173").split(",")
    )
    neighbors_file: str = field(default_factory=lambda: _env("HACKFIRE_NEIGHBORS_FILE"))
    crew_phone: str = field(default_factory=lambda: _env("HACKFIRE_CREW_PHONE"))

    deepfire_client_id: str = field(default_factory=lambda: _env("DEEPFIRE_CLIENT_ID"))
    deepfire_client_secret: str = field(default_factory=lambda: _env("DEEPFIRE_CLIENT_SECRET"))

    slng_api_key: str = field(default_factory=lambda: _env("SLNG_API_KEY"))
    slng_base_url: str = field(default_factory=lambda: _env("SLNG_BASE_URL"))

    nebius_api_key: str = field(default_factory=lambda: _env("NEBIUS_API_KEY"))
    nebius_base_url: str = field(default_factory=lambda: _env("NEBIUS_BASE_URL"))
    nebius_model: str = field(default_factory=lambda: _env("NEBIUS_MODEL"))

    ors_api_key: str = field(default_factory=lambda: _env("ORS_API_KEY"))


settings = Settings()
