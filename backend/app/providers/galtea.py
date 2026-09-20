"""Galtea: simulated residents that test the resident agent (`pnpm eval:galtea`), nothing else.

Evaluation only. Nothing in the app imports this module, and the SDK (`galtea` on PyPI) is a dev
dependency the deployed image does not install, so it is imported lazily. The SDK runs the
conversation simulator in this process: Galtea writes each resident's next line and our callback
answers as the agent. The SDK cannot create a product, so that one call goes to the REST API.
See https://docs.galtea.ai/sdk/tutorials/simulating-conversations.md,
https://docs.galtea.ai/sdk/api/simulator/simulate.md and
https://docs.galtea.ai/api-reference/products/create-product.md
"""

import tempfile
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import httpx

from ..config import settings

API_URL = "https://api.galtea.ai"
PLATFORM_URL = "https://platform.galtea.ai"
TIMEOUT_SECONDS = 30
# Galtea turns an uploaded dataset file into test cases in the background.
DATASET_READY_SECONDS = 180
# Recommended by Norma — fixed with Claude Opus 5 via Claude Code
# How often that background work is asked about while waiting for DATASET_READY_SECONDS.
DATASET_POLL_SECONDS = 3


class GalteaUnavailable(Exception):
    """No key, no SDK, or Galtea refused a request. The message says what to do."""


@dataclass(frozen=True)
class Simulation:
    session_id: str
    turns: int
    finished: bool
    stopping_reason: str | None


def configured() -> bool:
    return bool(settings.galtea_api_key)


def _sdk():
    try:
        import galtea
    except ImportError as error:
        raise GalteaUnavailable("The Galtea SDK is not installed. Run `pnpm bootstrap`: it is a dev dependency.") from error
    return galtea


def _not_found():
    from galtea.domain.exceptions.entity_not_found_exception import EntityNotFoundException

    return EntityNotFoundException


def connect():
    """A Galtea SDK client."""
    if not configured():
        raise GalteaUnavailable("GALTEA_API_KEY is not set. Get one at https://platform.galtea.ai/settings.")
    return _sdk().Galtea(api_key=settings.galtea_api_key)


def ensure_product(client, name: str, **fields: str) -> str:
    """The product's id, created through the REST API the first time. fields are the Product schema's."""
    try:
        return client.products.get_by_name(name=name).id
    except _not_found():
        pass
    response = httpx.post(
        f"{API_URL}/products",
        headers={"Authorization": f"Bearer {settings.galtea_api_key}"},
        json={"name": name, **fields},
        timeout=TIMEOUT_SECONDS,
    )
    if response.status_code >= 400:
        raise GalteaUnavailable(f"Galtea refused to create the product {name!r}: HTTP {response.status_code} {response.text[:300]}")
    return response.json()["id"]


def ensure_version(client, product_id: str, name: str, *, description: str, system_prompt: str) -> str:
    try:
        return client.versions.get_by_name(product_id=product_id, version_name=name).id
    except _not_found():
        pass
    version = client.versions.create(name=name, product_id=product_id, description=description, system_prompt=system_prompt)
    return version.id


def ensure_behavior_dataset(client, product_id: str, name: str, csv_text: str, *, expected: int, language: str) -> list:
    """The dataset's test cases, uploading csv_text as a behavior dataset the first time.

    Behavior dataset file format: https://docs.galtea.ai/concepts/product/dataset/behavior-datasets.md
    """
    try:
        dataset = client.datasets.get_by_name(product_id=product_id, dataset_name=name, type="BEHAVIOR")
    except _not_found():
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / f"{name}.csv"
            path.write_text(csv_text, encoding="utf-8")
            dataset = client.datasets.create(
                name=name, type="BEHAVIOR", product_id=product_id, dataset_file_path=str(path), language=language
            )
    deadline = time.monotonic() + DATASET_READY_SECONDS
    while True:
        cases = client.test_cases.list(dataset_id=dataset.id)
        if len(cases) >= expected:
            return cases
        status = str(client.datasets.get(dataset_id=dataset.id).status or "")
        if status.upper().endswith(("FAILED", "CANCELLED")) or time.monotonic() > deadline:
            raise GalteaUnavailable(
                f"Galtea dataset {name!r} ({dataset.id}) has {len(cases)} of {expected} test cases, status {status or 'unknown'}."
            )
        time.sleep(DATASET_POLL_SECONDS)  # Recommended by Norma — fixed with Claude Opus 5 via Claude Code


def simulate(client, version_id: str, test_case_id: str, respond: Callable[[str | None], str], *, max_turns: int) -> Simulation:
    """One simulated conversation, the agent speaking first as on a real call.

    respond gets the resident's last line (None to open the call) and returns what the agent says;
    an empty answer ends the conversation.
    """
    galtea = _sdk()

    class _Agent(galtea.Agent):
        def call(self, input_data: galtea.AgentInput) -> galtea.AgentResponse:
            return galtea.AgentResponse(content=respond(input_data.last_user_message_str()))

    session = client.sessions.create(version_id=version_id, test_case_id=test_case_id, is_production=False)
    result = client.simulator.simulate(session_id=session.id, agent=_Agent(), max_turns=max_turns, agent_goes_first=True)
    return Simulation(session.id, result.total_turns, result.finished, result.stopping_reason)
