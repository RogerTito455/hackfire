"""Give both voice agents' end_call a Spanish goodbye. `pnpm voice:goodbye`; `pnpm voice:deploy` runs it.

A push with `unmute deploy` replaces an agent and brings back SLNG's English "Thanks for calling.
Goodbye!", because unmute 0.5.5 cannot set end_call's goodbye (providers/voice.set_goodbye).
"""

from ..config import settings
from ..providers import voice

GOODBYE = "Hasta luego."


def main() -> None:
    for name, agent_id in (("resident", settings.slng_resident_agent_id), ("coordinator", settings.slng_coordinator_agent_id)):
        voice.set_goodbye(agent_id, GOODBYE)
        print(f"{name} agent {agent_id}: end_call says {GOODBYE!r}")


if __name__ == "__main__":
    main()
