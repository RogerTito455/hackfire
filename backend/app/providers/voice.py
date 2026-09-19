"""SLNG client: outbound calls and SMS.

TODO(voice): fill in once we have a key and a phone number from the SLNG mentors.
Endpoints are intentionally absent; take them from https://docs.slng.ai/llms.txt
rather than guessing.
"""


def call_resident(phone: str, neighbor_id: str) -> None:
    raise NotImplementedError("SLNG outbound calls are not wired yet")


def notify_crew(message: str) -> None:
    raise NotImplementedError("SLNG crew notifications are not wired yet")
