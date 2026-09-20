import pytest

from app.latency import parts, summarize, turns


# Items shaped like SLNG's livekit_session_report.chat_history.items (seconds since the epoch).
def resident(stopped: float, *, delay: float | None = None, spoke: bool = True) -> dict:
    metrics = {"stopped_speaking_at": stopped} if spoke else {"on_user_turn_completed_delay": 0.0}
    if delay is not None:
        metrics["end_of_turn_delay"] = delay
    return {"type": "message", "role": "user", "interrupted": False, "metrics": metrics}


def agent(started: float | None = None, *, interrupted: bool = False, **metrics: float) -> dict:
    if started is not None:
        metrics["started_speaking_at"] = started
    return {"type": "message", "role": "assistant", "interrupted": interrupted, "metrics": metrics}


TOOL = [{"type": "function_call"}, {"type": "function_call_output"}]


def test_a_turn_is_the_time_from_the_resident_stopping_to_the_agent_starting_and_the_greeting_is_not_a_turn() -> None:
    items = [
        {"type": "agent_handoff"},
        agent(started=90.0),  # the greeting: nobody spoke before it
        resident(stopped=100.0),
        agent(started=101.65),
    ]

    [turn] = turns(items)

    assert turn.latency == pytest.approx(1.65)
    assert turn.tool_call is False
    assert turn.interrupted is False


def test_a_turn_where_the_agent_calls_a_tool_first_counts_until_its_first_words() -> None:
    """The slow turns: no e2e_latency on the message that finally speaks, so SLNG's own figure misses them."""
    items = [
        resident(stopped=200.0),
        agent(llm_node_ttft=1.07),  # decides to call a tool: no speech yet
        TOOL[0],
        agent(started=201.8, tts_node_ttfb=0.28),  # "un momento", spoken while the tool runs
        TOOL[1],
        agent(started=210.0, llm_node_ttft=0.89),  # the answer that used the tool's result
    ]

    [turn] = turns(items)

    assert turn.latency == pytest.approx(1.8)
    assert turn.tool_call is True
    assert turn.slng_e2e is None


def test_a_second_message_of_the_same_resident_turn_is_not_a_new_turn() -> None:
    items = [resident(stopped=300.0), resident(stopped=0, spoke=False), agent(started=301.77)]

    assert [round(t.latency, 2) for t in turns(items)] == [1.77]


def test_a_resident_who_speaks_again_before_any_reply_is_answered_once() -> None:
    items = [resident(stopped=400.0), resident(stopped=402.0), agent(started=403.5)]

    assert [round(t.latency, 2) for t in turns(items)] == [1.5]  # measured from the last time they stopped


def test_an_agent_already_speaking_when_the_resident_finishes_is_not_the_reply() -> None:
    items = [resident(stopped=500.0), agent(started=499.0), agent(started=502.2)]

    assert [round(t.latency, 2) for t in turns(items)] == [2.2]


def test_a_turn_the_agent_never_answers_is_not_counted() -> None:
    assert turns([agent(started=1.0), resident(stopped=600.0)]) == []


def test_an_interrupted_reply_keeps_its_latency_and_is_flagged() -> None:
    items = [resident(stopped=700.0), agent(started=701.605, interrupted=True, e2e_latency=1.605)]

    [turn] = turns(items)

    assert turn.interrupted is True
    assert turn.latency == pytest.approx(1.605)
    assert turn.slng_e2e == pytest.approx(turn.latency)  # SLNG's figure and ours agree where it gives one


def test_the_parts_slng_times_are_collected_from_the_messages_that_have_them() -> None:
    items = [
        agent(started=1.0, tts_node_ttfb=0.157),
        resident(stopped=10.0, delay=1.2),
        agent(started=11.6, llm_node_ttft=0.87, tts_node_ttfb=0.29),
        resident(stopped=20.0, delay=0.357),
        agent(llm_node_ttft=1.07),
        resident(stopped=0, spoke=False),
    ]

    result = parts(items)

    assert result.llm_ttft == [0.87, 1.07]
    assert result.tts_ttfb == [0.157, 0.29]
    assert result.end_of_turn_delay == [1.2, 0.357]


def test_the_summary_is_the_median_and_the_worst_case() -> None:
    result = summarize([1.6, 1.4, 4.0, 1.8, 2.2])

    assert result is not None
    assert (result.count, result.median, result.worst) == (5, 1.8, 4.0)
    assert summarize([]) is None


def test_metrics_that_are_null_are_treated_as_absent() -> None:
    """An interrupted message can serialise a null timing; it must not break the report."""
    silent = agent(llm_node_ttft=None, tts_node_ttfb=None)
    silent["metrics"]["started_speaking_at"] = None
    items = [
        resident(stopped=800.0, delay=None),
        silent,
        agent(started=801.5, llm_node_ttft=None, tts_node_ttfb=0.2),
        resident(stopped=None),  # no end of speech: not a turn
    ]

    assert [round(t.latency, 2) for t in turns(items)] == [1.5]
    result = parts(items)
    assert result.llm_ttft == [] and result.tts_ttfb == [0.2] and result.end_of_turn_delay == []
