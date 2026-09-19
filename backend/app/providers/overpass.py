"""OpenStreetMap through the Overpass API, for one-off downloads into data/.

The main instance (overpass-api.de) and kumi.systems timed out on 2026-09-19 while the mail.ru
mirror answered, so every mirror is tried in turn.
"""

import httpx

MIRRORS = (
    "https://overpass-api.de/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
)
USER_AGENT = "HackFire hackathon (github.com/RogerTito455/hackfire)"


def query(overpass_ql: str, timeout: float = 45) -> list[dict]:
    """Run an Overpass QL query ([out:json]) and return its elements."""
    errors = []
    for mirror in MIRRORS:
        try:
            response = httpx.post(
                mirror, data={"data": overpass_ql}, headers={"User-Agent": USER_AGENT}, timeout=timeout
            )
            response.raise_for_status()
            return response.json()["elements"]
        except (httpx.HTTPError, ValueError, KeyError) as error:
            errors.append(f"{mirror}: {error}")
    raise RuntimeError("every Overpass mirror failed:\n" + "\n".join(errors))
