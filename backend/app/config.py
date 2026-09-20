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


def _list(name: str) -> list[str]:
    """Comma-separated values, spaces and trailing slashes forgiven. Empty when unset."""
    return [item.strip().rstrip("/") for item in _env(name).split(",") if item.strip()]


def _private_key(value: str) -> str:
    """A PEM key given inline, or read from the path given instead. Empty when unset or unreadable."""
    if not value or value.startswith("-----BEGIN"):
        return value.replace("\\n", "\n")
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = REPO_ROOT / path  # the backend runs from backend/, the key sits at the repo root
    return path.read_text(encoding="utf-8") if path.is_file() else ""


@dataclass(frozen=True)
class Settings:
    cors_origins: list[str] = field(
        default_factory=lambda: _origins("HACKFIRE_CORS_ORIGINS", "http://localhost:5173")
    )
    neighbors_file: str = field(default_factory=lambda: _env("HACKFIRE_NEIGHBORS_FILE"))
    # The registry itself as JSON, for a deployment where the file cannot be in the image (it holds
    # the team's real phone numbers). Wins over the files when set.
    neighbors_json: str = field(default_factory=lambda: _env("HACKFIRE_NEIGHBORS_JSON"))
    # The built dashboard (frontend/dist). Set in the Dockerfile; empty locally, where Vite serves it.
    dashboard_dir: str = field(default_factory=lambda: _env("HACKFIRE_DASHBOARD_DIR"))
    crew_phone: str = field(default_factory=lambda: _env("HACKFIRE_CREW_PHONE"))
    # The crews' room id, which is the last part of the link they are texted (app/crew_room.py).
    # Set it to a hard-to-guess word so the link survives a deploy; unset, a deploy changes it.
    crew_room: str = field(default_factory=lambda: _env("HACKFIRE_CREW_ROOM"))
    # Ring the crew phone on every new rescue, with the crew-caller agent (docs/setup/phone-calls.md).
    # Off by default: it dials a real phone. Needs SLNG_CREW_AGENT_ID and HACKFIRE_CREW_PHONE.
    crew_calls: bool = field(default_factory=lambda: _env("HACKFIRE_CREW_CALLS") == "1")
    # How many fire crews the plan shares the rescues between; the dashboard can change it.
    crews: int = field(default_factory=lambda: int(_env("HACKFIRE_CREWS", "2") or 2))
    # Twilio, for the crew SMS (providers/sms.py). All three or none.
    twilio_account_sid: str = field(default_factory=lambda: _env("TWILIO_ACCOUNT_SID"))
    twilio_auth_token: str = field(default_factory=lambda: _env("TWILIO_AUTH_TOKEN"))
    twilio_from_number: str = field(default_factory=lambda: _env("TWILIO_FROM_NUMBER"))
    # Where the dashboard is reachable, for the link in each crew alert.
    public_url: str = field(default_factory=lambda: _env("HACKFIRE_PUBLIC_URL", "http://localhost:5173").rstrip("/"))
    # The dashboard's Content-Security-Policy (app/main.py, docs/findings/2026-09-20-csp.md).
    # Extra sources beyond the built-in ones, comma-separated, added to connect-src: another
    # backend a dashboard is pointed at, a Vonage region, a tile mirror. HACKFIRE_PUBLIC_URL
    # is added on its own.
    csp_connect_origins: list[str] = field(default_factory=lambda: _list("HACKFIRE_CSP_CONNECT"))
    # Report the policy instead of enforcing it: the browser logs violations and blocks nothing.
    # The escape hatch if the policy ever gets in the way of a live demo.
    csp_report_only: bool = field(default_factory=lambda: _env("HACKFIRE_CSP_REPORT_ONLY") == "1")
    # The language of what the voice agents are told (tool answers, call data) and of the crew SMS.
    # The dashboard picks its own per request (Accept-Language). Any code in app/locales/.
    agent_locale: str = field(default_factory=lambda: _env("HACKFIRE_AGENT_LOCALE", "en"))
    # The crews and the residents are reached in their own language: Spanish for a fire in Spain.
    crew_locale: str = field(default_factory=lambda: _env("HACKFIRE_CREW_LOCALE", "es"))
    resident_locale: str = field(default_factory=lambda: _env("HACKFIRE_RESIDENT_LOCALE", "es"))
    # Text a resident who is leaving their way out (app/maps.py). Off by default: it texts a real
    # phone from the registry. Needs Vonage SMS configured.
    resident_sms: bool = field(default_factory=lambda: _env("HACKFIRE_RESIDENT_SMS") == "1")
    # The active scenario (app/scenario.py): which fire is replayed, where and when, from which files.
    # An id of data/scenarios/<id>.json, or a path to a scenario file. See docs/setup/new-scenario.md.
    scenario: str = field(default_factory=lambda: _env("HACKFIRE_SCENARIO", "el-tiemblo-2026-07-23"))
    # The replay moment the calls happen at, instead of the scenario's own `scenario_time`: routes
    # avoid the fire burned up to then. None (unset) keeps the scenario's.
    scenario_time_override: datetime | None = field(
        default_factory=lambda: datetime.fromisoformat(value) if (value := _env("HACKFIRE_SCENARIO_TIME")) else None
    )

    deepfire_client_id: str = field(default_factory=lambda: _env("DEEPFIRE_CLIENT_ID"))
    deepfire_client_secret: str = field(default_factory=lambda: _env("DEEPFIRE_CLIENT_SECRET"))

    slng_api_key: str = field(default_factory=lambda: _env("SLNG_API_KEY"))
    # The deployed resident agent (voice/README.md), which the call campaign and the dashboard's
    # "Talk" button start conversations with.
    slng_resident_agent_id: str = field(
        default_factory=lambda: _env("SLNG_RESIDENT_AGENT_ID", "0f035ccc-10d8-4de8-8142-abf4dc484fd8")
    )
    # The deployed coordinator agent (voice/coordinator/), which the dashboard's "Ask the agent" talks to.
    # The agent that phones the crew when a rescue comes in: the coordinator agent in the region of
    # the outbound connection, so it can dial out (voice/README.md).
    slng_crew_agent_id: str = field(default_factory=lambda: _env("SLNG_CREW_AGENT_ID"))
    slng_coordinator_agent_id: str = field(
        default_factory=lambda: _env("SLNG_COORDINATOR_AGENT_ID", "6d1a743a-4a0e-42b2-aa3f-5052c247137c")
    )
    # Vonage (#18): live video from a resident who needs rescue, with captions, and the SMS with
    # the link. The private key is the PEM text (as Railway holds it) or a path to the .key file.
    vonage_application_id: str = field(default_factory=lambda: _env("VONAGE_APPLICATION_ID"))
    vonage_private_key: str = field(default_factory=lambda: _private_key(_env("VONAGE_PRIVATE_KEY")))
    vonage_sms_from: str = field(default_factory=lambda: _env("VONAGE_SMS_FROM", "HackFire"))
    # Off until an outbound SIP trunk is attached to the agent in SLNG: SLNG supplies no numbers.
    phone_calls: bool = field(default_factory=lambda: _env("HACKFIRE_PHONE_CALLS") == "1")
    slng_base_url: str = field(default_factory=lambda: _env("SLNG_BASE_URL"))

    # The backend's LLM (typed answers, pnpm eval:triage): SLNG's OpenAI-compatible Context Router,
    # with SLNG_API_KEY and the model the voice agents think with.
    slng_llm_url: str = field(
        default_factory=lambda: _env("SLNG_LLM_URL", "https://eu-north.context-router.slng.ai/v1").rstrip("/")
    )
    slng_llm_model: str = field(
        default_factory=lambda: _env("SLNG_LLM_MODEL", "bedrock-mantle/nvidia.nemotron-super-3-120b:latest")
    )

    # openrouteservice, in the order they are tried: ORS_API_KEY, then ORS_API_KEY2 and ORS_API_KEY3.
    # The free plan gives 2,000 directions a day per key, so `pnpm data:routes` moves to the next one
    # when a key's daily quota is gone (providers/routing.py). Empty ones are skipped.
    ors_api_keys: list[str] = field(
        default_factory=lambda: [
            key for name in ("ORS_API_KEY", "ORS_API_KEY2", "ORS_API_KEY3") if (key := _env(name))
        ]
    )

    # The audit log (app/audit.py): one JSON object per line, append-only, git-ignored. Never holds
    # a phone number. docs/setup/operations.md.
    audit_file: Path = field(
        default_factory=lambda: Path(_env("HACKFIRE_AUDIT_FILE", str(DATA_DIR / "audit.jsonl")))
    )

    # Galtea, for `pnpm eval:galtea` only (simulated residents against the resident agent). The app never reads it.
    galtea_api_key: str = field(default_factory=lambda: _env("GALTEA_API_KEY"))

    # The DGT's road incidents (DATEX II v3, public, no key). It redirects to the current version.
    dgt_feed_url: str = field(
        default_factory=lambda: _env(
            "DGT_FEED_URL", "https://nap.dgt.es/datex2/v3/dgt/SituationPublication/datex2_v36.xml"
        )
    )

    # Public Overpass instances come and go; set OVERPASS_URL to another one if this refuses connections.
    overpass_url: str = field(
        default_factory=lambda: _env("OVERPASS_URL", "https://overpass-api.de/api/interpreter")
    )
    # Tried in order after OVERPASS_URL when it is busy (429, 504) or down. Comma-separated.
    overpass_mirrors: list[str] = field(
        default_factory=lambda: [
            url.strip()
            for url in _env(
                "OVERPASS_MIRRORS",
                "https://overpass.openstreetmap.fr/api/interpreter,https://overpass.private.coffee/api/interpreter",
            ).split(",")
            if url.strip()
        ]
    )


settings = Settings()
