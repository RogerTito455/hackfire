"""The sentences the backend writes: route directions, evacuation orders, the fire line the agents
say, and crew alerts.

Every sentence lives in app/locales/<code>.json, English (en.json) being the reference and the
fallback; adding a language is adding one file with the same keys (tests/test_i18n.py checks them).
Placeholders are {name}; a sentence that varies with a number is an object of plural forms picked by
`count`.

The locale is per request, in a context variable: the dashboard's requests follow ?lang= or its
Accept-Language header, the voice agents' tools and call data follow HACKFIRE_AGENT_LOCALE, and the
crew SMS HACKFIRE_CREW_LOCALE (main.py and config.py).
"""

import json
import re
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from functools import cache
from pathlib import Path

LOCALES_DIR = Path(__file__).parent / "locales"
REFERENCE = "en"

_current: ContextVar[str] = ContextVar("locale", default=REFERENCE)


@cache
def catalogue() -> dict[str, dict]:
    return {path.stem: json.loads(path.read_text(encoding="utf-8")) for path in sorted(LOCALES_DIR.glob("*.json"))}


def resolve(tag: str | None) -> str:
    """A locale we have for a BCP 47 tag ("es-ES" -> "es"), else English."""
    if not tag:
        return REFERENCE
    tag = tag.strip().lower().replace("_", "-")
    if tag in catalogue():
        return tag
    language = tag.split("-")[0]
    return language if language in catalogue() else REFERENCE


def negotiate(accept_language: str | None) -> str:
    """The best locale for an Accept-Language header, by its q weights."""
    ranked = []
    for position, part in enumerate((accept_language or "").split(",")):
        tag, _, params = part.strip().partition(";")
        weight = 1.0
        if params.strip().startswith("q="):
            try:
                weight = float(params.strip()[2:])
            except ValueError:
                weight = 0.0
        if tag and tag != "*" and weight > 0:
            ranked.append((-weight, position, tag))
    for _, _, tag in sorted(ranked):
        language = tag.strip().lower().split("-")[0]
        if language in catalogue():
            return language
    return REFERENCE


def current() -> str:
    return _current.get()


def set_current(locale: str | None):
    """Sets the locale for this request; returns the token to reset it with."""
    return _current.set(resolve(locale))


def reset(token) -> None:
    _current.reset(token)


@contextmanager
def using(locale: str | None) -> Iterator[None]:
    token = set_current(locale)
    try:
        yield
    finally:
        reset(token)


def _plural_form(locale: str, count: float) -> str:
    # English and Spanish: one for exactly 1. A language with other rules adds them here.
    return "one" if count == 1 else "other"


def _lookup(messages: dict, key: str):
    node = messages
    for part in key.split("."):
        if not isinstance(node, dict) or part not in node:
            return None
        node = node[part]
    return node


def t(key: str, locale: str | None = None, **values) -> str:
    """The sentence for `key` in `locale` (default: the request's), placeholders filled in."""
    code = resolve(locale) if locale else current()
    value = _lookup(catalogue().get(code, {}), key)
    if value is None:
        value = _lookup(catalogue()[REFERENCE], key)
    if isinstance(value, dict) and "count" in values:
        value = value.get(_plural_form(code, values["count"]), value.get("other"))
    if not isinstance(value, str):
        raise KeyError(f"no text for {key!r}")
    return re.sub(r"\{(\w+)\}", lambda match: str(values.get(match[1], match[0])), value)
