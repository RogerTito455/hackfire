from dataclasses import replace

import pytest

from app import audit, scenario
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


@pytest.fixture(autouse=True)
def fresh_audit_log(tmp_path, monkeypatch: pytest.MonkeyPatch) -> audit.AuditLog:
    """Every test writes its own audit file, never data/audit.jsonl."""
    log = audit.AuditLog(tmp_path / "audit.jsonl")
    monkeypatch.setattr(audit, "log", log)
    return log


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--transcripts",
        default=None,
        help="eval_galtea.py: add each scenario's turns and last report_status to this JSON file "
        "(docs/services/galtea.md)",
    )


@pytest.fixture(autouse=True)
def no_dgt_network(monkeypatch: pytest.MonkeyPatch, tmp_path_factory: pytest.TempPathFactory):
    """Live operations add the DGT's official incidents: no test reaches the real feed or its cache
    file. A test that wants DGT data patches live_dgt._fetch itself (tests/test_live_dgt.py)."""
    import httpx

    from app import live_dgt

    def offline() -> tuple[list[dict], str | None]:
        raise httpx.ConnectError("no network in tests")

    monkeypatch.setattr(live_dgt, "CACHE_FILE", tmp_path_factory.mktemp("dgt") / "live_dgt.json")
    monkeypatch.setattr(live_dgt, "_fetch", offline)
    live_dgt.reset_cache()
    yield
    live_dgt.reset_cache()
