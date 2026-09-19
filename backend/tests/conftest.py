import pytest

from app.state import state


@pytest.fixture(autouse=True)
def fresh_replay_clock() -> None:
    """Every test starts with no replay time set, as after a server restart."""
    state.replay_time = None
