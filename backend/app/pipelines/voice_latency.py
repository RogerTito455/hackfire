"""How long the resident waits for the resident agent to answer, from SLNG's own call reports (#14).

    pnpm voice:latency                       # calls since the current agent version was deployed
    pnpm voice:latency --since 2026-09-19T16:52:54Z
    pnpm voice:latency --all                 # every finished call, whatever the version

Needs SLNG_API_KEY for the project that holds the agent, and SLNG_RESIDENT_AGENT_ID. The latency of
each turn is the time from the resident finishing speaking to the agent starting (app/latency.py
explains why that, and not SLNG's `e2e_latency`). Prints the numbers for the pitch slide and how they
were computed. Only reads. Exit code 1 when the numbers should not be used yet: fewer than
MIN_TURNS turns, or a call whose report could not be read or is not ready.
"""

import sys
from datetime import UTC, datetime

from ..latency import Turn, parts, summarize, turns
from ..providers import voice

MIN_TURNS = 10  # SLNG's brief asks for real numbers: at least ten turns


def when(text: str) -> datetime:
    """An ISO 8601 time as an exact UTC moment; one with no offset is taken as UTC."""
    moment = datetime.fromisoformat(text.replace("Z", "+00:00"))
    return moment.astimezone(UTC) if moment.tzinfo else moment.replace(tzinfo=UTC)


def main() -> None:
    argv = sys.argv[1:]
    if not voice.web_sessions_configured():
        sys.exit("Set SLNG_API_KEY and SLNG_RESIDENT_AGENT_ID (the project that holds the resident agent).")

    since: datetime | None = None
    if "--all" not in argv:
        deployed = when(voice.resident_agent()["updated_at"])
        since = when(argv[argv.index("--since") + 1]) if "--since" in argv else deployed
        print(f"resident agent updated at {deployed:%Y-%m-%d %H:%M:%S} UTC")
    print("using calls that started " + (f"after {since:%Y-%m-%d %H:%M:%S} UTC" if since else "at any time"))

    all_turns: list[Turn] = []
    pieces: dict[str, list[float]] = {"llm_ttft": [], "tts_ttfb": [], "end_of_turn_delay": []}
    used, pending, failed = [], [], []
    for summary in sorted((c for c in voice.list_calls() if c.get("call_started_at")), key=lambda c: when(c["call_started_at"])):
        started = when(summary["call_started_at"])
        if (since and started <= since) or summary.get("call_ended_at") is None:
            continue  # an older version, or still in progress: its report is not final yet
        label = f"  {started:%H:%M:%S}  {summary['id'][:8]}"
        try:
            report = voice.get_call(summary["id"]).get("livekit_session_report")
        except voice.VoiceUnavailable as error:
            print(f"{label}  could not be read ({error}); left out")
            failed.append(summary["id"])
            continue
        if not report:
            print(f"{label}  ended but its report is not ready yet; left out, rerun in a minute")
            pending.append(summary["id"])
            continue
        items = report.get("chat_history", {}).get("items", [])
        call_turns = turns(items)
        print(f"{label}  {len(call_turns):>2} turns  ({summary.get('status')})")
        if call_turns:
            used.append(summary["id"])
            all_turns += call_turns
            for name, values in vars(parts(items)).items():
                pieces[name].extend(values)

    overall = summarize([t.latency for t in all_turns])
    incomplete = bool(pending or failed)
    if overall is None:
        print("\nNo turns yet: make test calls with the current agent, hang up, and rerun once they have ended.")
        sys.exit(1)

    print(f"\n{overall.count} turns in {len(used)} calls")
    print(f"  median {overall.median:.2f} s   worst {overall.worst:.2f} s   <- the two numbers for the slide")
    for label, part in (
        ("answered directly", summarize([t.latency for t in all_turns if not t.tool_call])),
        ("agent used a tool first", summarize([t.latency for t in all_turns if t.tool_call])),
    ):
        if part:
            print(f"  {label:24} {part.count:>2} turns, median {part.median:.2f} s, worst {part.worst:.2f} s")
    print("median of each part (they overlap: the model starts before the end of turn is decided):")
    for label, name in (("end-of-turn wait", "end_of_turn_delay"), ("model, time to first token", "llm_ttft"), ("voice, time to first byte", "tts_ttfb")):
        part = summarize(pieces[name])
        if part:
            print(f"  {label:28} {part.median:.2f} s  ({part.count} samples)")
    slng = [(t.latency, t.slng_e2e) for t in all_turns if t.slng_e2e is not None]
    if slng:
        print(f"check: SLNG's own e2e_latency exists for {len(slng)} turns and differs from ours by at most {max(abs(a - b) for a, b in slng):.3f} s")
    print(f"interrupted replies: {sum(t.interrupted for t in all_turns)}")

    if overall.count < MIN_TURNS:
        print(f"\nNOT FINAL: SLNG asks for at least {MIN_TURNS} turns; make more calls.")
    if incomplete:
        print(f"NOT FINAL: {len(pending)} call(s) not ready and {len(failed)} unreadable are left out; rerun.")
    if overall.count < MIN_TURNS or incomplete:
        sys.exit(1)


if __name__ == "__main__":
    main()
