from dataclasses import replace

import pytest

from app import scenario
from app.config import settings
from app.state import state


@pytest.fixture(autouse=True)
def fresh_replay_clock() -> None:
    """Every test starts with no replay time set, as after a server restart."""
    state.replay_time = None


@pytest.fixture(autouse=True)
def sample_registry(monkeypatch: pytest.MonkeyPatch) -> None:
    """Tests run against the active scenario's tracked registry, never a developer's private registry,
    whether it sits in neighbors.local.json or in HACKFIRE_NEIGHBORS_JSON."""
    monkeypatch.setattr("app.state.settings", replace(settings, neighbors_json=""))
    monkeypatch.setattr("app.state._registry_candidates", lambda: [scenario.current().files.registry])
    state.load()


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--transcripts",
        default=None,
        help="eval_galtea.py: add each scenario's turns and last report_status to this JSON file "
        "(docs/services/galtea.md)",
    )
