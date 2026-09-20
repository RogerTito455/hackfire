"""Voice latency from SLNG's session reports: how long the resident waits for the agent.

A report's `livekit_session_report.chat_history.items` lists messages and tool calls with timings.
For each time the resident finishes speaking, the latency is the time until the agent's first words:

    latency = agent started_speaking_at - resident stopped_speaking_at

Not SLNG's own `e2e_latency`: it is only present when the agent answers directly. When the agent
calls a tool before it speaks (the slow turns), the message that finally speaks carries no
`e2e_latency`, so a median over it would leave the slowest turns out. Where SLNG does give one, it
equals this figure (checked on a real call: 1.653 s both ways).
"""

from collections.abc import Sequence
from dataclasses import dataclass
from statistics import median


@dataclass(frozen=True)
class Turn:
    """One exchange: the resident finished speaking, then the agent began to."""

    latency: float
    tool_call: bool
    interrupted: bool
    slng_e2e: float | None


@dataclass(frozen=True)
class Summary:
    count: int
    median: float
    worst: float


@dataclass(frozen=True)
class Parts:
    """The pieces SLNG times, each over every message that has it."""

    llm_ttft: list[float]
    tts_ttfb: list[float]
    end_of_turn_delay: list[float]


def _metrics(item: dict) -> dict:
    return item.get("metrics") or {}


def _timing(item: dict, name: str) -> float | None:
    """A timing of a message. SLNG may leave it out or serialise it as null: both mean it is unknown."""
    value = _metrics(item).get(name)
    return value if isinstance(value, (int, float)) else None


def turns(items: Sequence[dict]) -> list[Turn]:
    """Every turn of a call. The greeting has no turn before it, so it is not one."""
    found = []
    for index, item in enumerate(items):
        if item.get("type") != "message" or item.get("role") != "user":
            continue
        heard = _timing(item, "stopped_speaking_at")
        if heard is None:  # a continuation of the same turn, not a new one
            continue
        tool_call = False
        for later in items[index + 1 :]:
            if later.get("type") == "function_call":
                tool_call = True
            elif later.get("type") == "message":
                if later.get("role") == "user" and _timing(later, "stopped_speaking_at") is not None:
                    break  # the resident spoke again before the agent said anything
                started = _timing(later, "started_speaking_at")
                if later.get("role") == "assistant" and started is not None and started >= heard:
                    found.append(
                        Turn(
                            latency=started - heard,
                            tool_call=tool_call,
                            interrupted=bool(later.get("interrupted")),
                            slng_e2e=_timing(later, "e2e_latency"),
                        )
                    )
                    break
    return found


def parts(items: Sequence[dict]) -> Parts:
    def collect(role: str, name: str) -> list[float]:
        messages = (i for i in items if i.get("type") == "message" and i.get("role") == role)
        return [value for value in (_timing(m, name) for m in messages) if value is not None]

    return Parts(
        llm_ttft=collect("assistant", "llm_node_ttft"),
        tts_ttfb=collect("assistant", "tts_node_ttfb"),
        end_of_turn_delay=collect("user", "end_of_turn_delay"),
    )


def summarize(values: Sequence[float]) -> Summary | None:
    return Summary(len(values), median(values), max(values)) if values else None
