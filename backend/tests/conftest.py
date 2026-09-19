from dataclasses import replace

import pytest

from app.config import DATA_DIR, settings
from app.state import state


@pytest.fixture(autouse=True)
def fresh_replay_clock() -> None:
    """Every test starts with no replay time set, as after a server restart."""
    state.replay_time = None


@pytest.fixture(autouse=True)
def sample_registry(monkeypatch: pytest.MonkeyPatch) -> None:
    """Tests run against the sample registry, never a developer's private registry, whether it sits in
    neighbors.local.json or in HACKFIRE_NEIGHBORS_JSON."""
    monkeypatch.setattr("app.state.settings", replace(settings, neighbors_json=""))
    monkeypatch.setattr("app.state._REGISTRY_CANDIDATES", [DATA_DIR / "neighbors.sample.json"])
    state.load()


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--transcripts",
        default=None,
        help="eval_galtea.py: add each scenario's turns and last report_status to this JSON file "
        "(docs/services/galtea.md)",
    )
