# The Norma pass: one XXE in the DGT feed parser, and what we chose not to change

**Date:** 2026-09-20 · **Area:** Norma (QualityClouds), code quality

Extension 1 (#17): one scan, at least one fix, one rescan, and the before/after delta.

## How it was checked

**Not with a full repository scan.** `link_repository` refuses this repo:

```
{"outcome": "failed", "reason": "auto_import_not_available",
 "message": "No repository matching this remote is linked to your organisation yet,
             and automatic import isn't available yet in this environment."}
```

A full scan, and therefore `get_open_issues`, needs the repository imported in the Norma portal
first, which cannot be done from the MCP server for a private repo. That answers the open question
that was in `docs/services/norma.md`.

So every number below comes from `live_check`, which works unlinked and is deterministic: same
file, same rules, same verdict. One call per file, `min_severity: "medium"`, the file's exact
content passed in. `live_check` picks the ruleset from the file extension, so the counts are
directly comparable before and after. Two counts are reported per file: **≥ medium** (what
`min_severity` returns) and **total**, which Norma counts across every severity including info and
low.

Rulesets Norma applied: `python-norma-ruleset`, `fastapi-norma-ruleset` and
`sqlalchemy-norma-ruleset` for `.py`; `typescript-norma-ruleset`, `javascript-norma-ruleset`,
`react-norma-ruleset`, `nodejs-norma-ruleset`, `supabase-norma-ruleset` and `vite-norma-ruleset`
for the frontend; `vite-norma-ruleset` for the HTML entry points; `nodejs-norma-ruleset` for
`package.json`. (Norma detects the stack itself. We use no SQLAlchemy and no Supabase; those two
rulesets simply find nothing.)

## Before and after

The eight files the pass covers, in scan order.

| File | Before (≥ med / total) | After (≥ med / total) | Rules found |
|---|---|---|---|
| `backend/app/main.py` | 34 / 80 | **33 / 79** | `fa-scl-no-pagination` ×7 (HIGH), `fa-mng-no-status-code` ×19 (MED), `fa-mng-dict-response` ×7 (MED), `fa-mnt-no-typing-param` ×1 (MED) |
| `backend/app/state.py` | 0 / 0 | 0 / 0 | — clean |
| `backend/app/providers/voice.py` | 0 / 0 | 0 / 0 | — clean |
| `backend/app/providers/dgt.py` | 1 / 1 | **0 / 0** | `py-sec-xml-xxe` ×1 (HIGH) |
| `frontend/src/services/api.ts` | 7 / 7 | 7 / 7 | `js-mng-loopback-url` ×1 (HIGH), `js-no-error-handling-async` ×3 (HIGH), `js-fetch-no-timeout` ×3 (MED) |
| `frontend/index.html` | 2 / 2 | **1 / 1** | `vite-missing-csp` ×1 (HIGH), `vite-missing-referrer-policy` ×1 (MED) |
| `frontend/vite.config.ts` | 0 / 0 | 0 / 0 | — clean |
| `package.json` | 0 / 0 | 0 / 0 | — clean |
| **Total** | **44 / 90** | **41 / 87** | |

Security findings went from 3 to 1, and the only remaining one is the CSP, accepted below.

`frontend/src/services/api.ts` and `frontend/vite.config.ts` were both scanned with
`coverage.reduced: true` — Norma reports that one semgrep rule could not be evaluated within its
fault-isolation budget. The same reduction applied before and after, so the comparison still holds,
but those two files are not a complete check.

## The wider sweep

With time left before the submission, the rest of the repo was scanned the same way: the other 42
backend files (every non-empty `.py` under `backend/app/`, `providers/` and `pipelines/`) and the 25
main frontend files — 67 files in all. Nothing there was changed; it is a picture of where the repo
stands.

### The backend

**No security rule fired in any of the 42 backend files.** That includes every path that handles a key, a
token or a phone number: `config.py`, `audit.py`, `providers/deepfire.py`, `providers/sms.py`,
`providers/vonage.py`, `rescue_video.py` and `crew_room.py` all came back clean. `config.py` and
`audit.py` are the two that carry the weight — every key goes through `_env`, and `audit.py`'s
`_PHONE` redaction and `_FORBIDDEN_KEYS` drop keep numbers out of the log — and both scan clean.

| Where | Files | Files with findings | ≥ med | What fired |
|---|---|---|---|---|
| `backend/app/pipelines/` | 8 | 8 | 26 | `py-maint-no-print` (MED), `py-mng-sys-exit-lib` (MED, in `common.py` and `fetch_zones.py`) |
| `backend/app/` core | 14 | 3 | 7 | `fa-scl-global-state` ×2 (HIGH), `fa-mng-dict-response` ×4, `fa-mnt-no-typing-param` ×1 (MED) |
| `backend/app/` rest + `providers/` | 20 | 1 | 1 | `fa-mng-dict-response` ×1 (MED) |
| **Total** | **42** | **12** | **34** | |

Three things are worth saying about those 34 findings, because the honest answer to most of them is
"the rule matched something that is not what it is looking for":

- **`py-maint-no-print` (the bulk of the 26)** is entirely inside `backend/app/pipelines/`, the one-off data
  downloads run as `pnpm data:hotspots`, `pnpm data:zones`, `pnpm check:routes` and friends. The
  prints are the CLI's output — `check_routes.py`'s `OK:` / `NOT OK:` verdicts are the whole point
  of the command. Routing them through `logging` would make the tools quieter, not more
  observable. The request path already uses `logging.getLogger(...)` throughout and scans clean.
- **`fa-scl-global-state` (HIGH ×2)** in `impact.py` is a false positive: the flagged `polygons` is
  a local variable inside a `@cached` function, not module state. The genuinely module-level caches
  elsewhere (`evacuation._memory`, `live_operations._places`, `live_spread._snapshot`,
  `live_dgt._snapshot`, `provider_status._results`) are the documented architecture — CLAUDE.md's
  "demo mode comes first", a single process, each cache already behind a `Lock`/`RLock`. The rule's
  remediation is "move to Redis", which is out of scope by the guardrail.
- **`fa-mng-dict-response` and `fa-mnt-no-typing-param` outside `main.py`** matched `@cached`
  loaders and a pydantic validator that have no route decorator at all — the FastAPI ruleset keying
  on `-> dict[...]` under a decorator. `models.py:127`'s untyped-looking parameter is annotated
  `value: object` on purpose, because SLNG passes tool arguments through unchecked
  (`docs/findings/2026-09-19-slng-tool-arguments-unchecked.md`).

The one backend finding that is a real (if small) design point is `py-mng-sys-exit-lib` in
`backend/app/pipelines/common.py`: `write_or_compare` calls `sys.exit(1)` on a `--check` mismatch,
so any future importer gets the process killed instead of an exception. Today its only callers are
`__main__` scripts, where exiting is exactly what should happen.

### The frontend

25 files — `App.tsx`, the hooks, the services and the larger `ui/` components. 14 clean, 11 with
findings, 33 findings at medium and above. Every one of these calls reported
`coverage.reduced: true`, so this is not a complete check of the frontend.

| Rule | Sev | × | Where |
|---|---|---|---|
| `js-no-error-handling-async` | HIGH | 15 | `services/videoCall.ts` ×11, `App.tsx` ×2, `hooks/useTriage.ts` ×2 |
| `rct-prf-setstate-in-useeffect` | HIGH | 4 | `ui/TriageMap.tsx`, `hooks/useCrewRoom.ts` ×2, `ui/BottomSheet.tsx` |
| `rct-unsafe-href-binding` | HIGH | 4 | `ui/landing/Landing.tsx` ×3, `ui/LiveOperationsPanel.tsx` |
| `js-inner-html-assignment` | HIGH | 3 | `ui/TriageMap.tsx` |
| `js-empty-catch-block` | HIGH | 3 | `ui/i18n.tsx` ×2, `hooks/useClosures.ts` |
| `js-nested-ternary` | MED | 3 | `ui/OrdersPanel.tsx` ×2, `ui/TriageMap.tsx` |
| `js-function-in-loop` | MED | 1 | `ui/TriageMap.tsx` |

Each was traced to its source rather than taken at face value, and most do not survive that:

- **`rct-unsafe-href-binding` ×4** are false positives. The two sources are
  `liveOperationsCapUrl()`, which builds a same-origin path with `encodeURIComponent` on the one
  variable segment, and `DEMO_URL`, a literal `'/'` in `src/landing.tsx`. No user input reaches
  either.
- **`rct-prf-setstate-in-useeffect` ×4** are false positives too: none is a synchronous `setState`
  in an effect body. They sit inside MapLibre's `load` callback, an async IIFE and a
  `ResizeObserver` callback. The codebase already uses the adjust-during-render pattern where it is
  actually needed, with comments saying so.
- **`js-inner-html-assignment` ×3** in `TriageMap.tsx` build MapLibre marker DOM from
  `ui/markers.ts`, which concatenates hard-coded SVG with a colour from `theme.ts` and an icon name
  from a fixed union. No external data reaches them, and MapLibre markers need real DOM nodes, so
  JSX is not an option — this is the "no icon or SVG libraries" convention doing its job.
- **`js-no-error-handling-async` ×11 in `services/videoCall.ts`** is the same deliberate boundary as
  `services/api.ts`: rejections propagate to `useRescueVideo` and `useCrewRoom`, which both catch
  and set an `'error'` state. Catching twice would swallow that transition.

Two are worth carrying forward as real (small) work, and are listed under *What remains*: the
unhandled rejection behind the reset button, and the three empty catch blocks.

## What was fixed

### 1. `py-sec-xml-xxe` (HIGH, security) — `backend/app/providers/dgt.py`

The one that mattered. `parse()` read the DGT's public DATEX II feed — about 3 MB of third-party
XML fetched over the network on every live-mode refresh — with the standard library:

```python
root = ET.fromstring(body)
```

Stdlib `ElementTree` expands internal entities, so a hostile or corrupted feed could have pushed the
backend into an entity-expansion blow-up (billion laughs) during a demo that is meant to stay up.
We do not control that document and we re-fetch it every five minutes.

Fixed as Norma's remediation says: `uv add defusedxml`, then parse with
`defusedxml.ElementTree.fromstring`, which refuses entity expansion and external entities. The
`except` clause now also catches `defusedxml.common.DefusedXmlException`, so a refused document
still surfaces as the `ValueError` `live_dgt.overview()` and `backend/tests/test_live_dgt.py`
already expect — the feed simply becomes "unavailable" rather than taking the process with it.
`ElementTree` stays imported for the element types and for walking the tree.

Checked by hand against a small entity bomb, which now comes back as the ordinary "unavailable"
error instead of expanding:

```
>>> dgt.parse(b'<?xml version="1.0"?><!DOCTYPE lolz [<!ENTITY lol "lol"> ...]><payload>&lol2;</payload>')
ValueError: DGT feed is not plain DATEX II XML: EntitiesForbidden(name='lol', ...)
>>> dgt.parse(b'not xml at all')
ValueError: DGT feed is not plain DATEX II XML: syntax error: line 1, column 0
```

`backend/app/cap.py` also uses `ElementTree`, but only to *build* the outgoing CAP 1.2 document
(`ET.Element`, `SubElement`, `tostring`). It parses no untrusted input, so it was deliberately left
alone.

### 2. `vite-missing-referrer-policy` (MEDIUM, security) — `frontend/index.html`

No referrer policy meant the full URL went out as the `Referer` header to every cross-origin
resource. That is not academic here: the dashboard's own URLs carry identifiers — `/?rescue=<id>`
from a crew alert SMS, `/v/<link id>` for a resident's single-use video link, `/crew/<room id>` —
and the page loads map tiles, LiveKit and Vonage from other origins. One line:

```html
<meta name="referrer" content="strict-origin-when-cross-origin" />
```

Cross-origin requests now send the origin only; same-origin requests keep the full URL.

`frontend/about.html`, the other Vite entry point, scans clean for this rule and its URLs carry no
identifier, so it was left as it is.

### 3. `fa-mnt-no-typing-param` (MEDIUM, maintainability) — `backend/app/main.py`

The `request_locale` HTTP middleware took `call_next` with no annotation and returned unannotated.
Annotated as `Callable[[Request], Awaitable[Response]]` returning `Response`. It is a middleware,
not a route, so FastAPI never used those annotations for validation and nothing changes at runtime.

`pnpm check` passes after all three (backend tests, icon check, locale check, frontend build).

## What was accepted, and why

Everything left is a deliberate choice for a demo that has to run in front of a jury today. Norma is
right about the general case in each of these; the reasons are specific to this codebase.

### `vite-missing-csp` (HIGH) — `frontend/index.html`

The only security finding we did not fix, and the one to be honest about. A Content Security Policy
here would have to allow MapLibre GL's blob workers, the tile host, the backend origin, the LiveKit
WebSocket and the Vonage video SDK. Getting one of those sources wrong produces a blank map or a
call that will not connect, and it cannot be verified without exercising the whole demo in a
browser. Writing an untested CSP into the entry point hours before the submission is a worse risk
than the one it removes: the dashboard loads no third-party script at runtime and renders no
user-supplied HTML.

It also belongs somewhere else. Norma's own remediation note says to set the CSP as a response
header for server-rendered setups, and the deployed image serves this page from FastAPI
(`serve_dashboard` in `backend/app/main.py`). A header there can be rolled out, tested and tightened
report-only first — which is the right way to do it, and the way to do it after the hackathon.

### `fa-scl-no-pagination` (HIGH ×7) — `backend/app/main.py`

`/api/neighbors`, `/api/rescues`, `/api/alerts`, `/api/orders`, `/api/safe-points`, `/api/closures`
and `/api/status/providers`. The rule is about payloads that grow unbounded with the data. None of
these do: each is an in-memory collection whose size is fixed by the active scenario — the
residents' registry, the zones with residents, the candidate safe points, the handful of roads a
coordinator has cut, the fixed list of external services. The dashboard polls all of them and draws
every item on one screen, so paginating would mean paging in the client to reassemble a list it
already shows whole.

The one endpoint here that *does* grow without limit is the audit log — and it already takes
`limit: int = Query(default=15, ge=1, le=1000)`.

### `fa-mng-no-status-code` (MEDIUM ×19) — `backend/app/main.py`

These POSTs are commands and queries, not creations: start a call, approve an order, move the
replay clock, ask for a rescue route. 200 is the correct status for them; 201 would be wrong. Six of
the nineteen are the `/tools/*` endpoints, which are the contract with the SLNG voice agents
(PLAN.md section 6) — changing their status codes is a contract change, not a cleanup. The one route
that really does return no content, `DELETE /api/closures/{closure_id}`, already declares
`status_code=204`.

### `fa-mng-dict-response` (MEDIUM ×7) — `backend/app/main.py`

`/health` and six endpoints that pass through structures we do not own: the impact timeline, the
GeoJSON-shaped live fires and spread, the live operations bundle, the DGT overview, the fire area.
Modelling them in pydantic means freezing the shape of third-party payloads we are still learning,
and Deepfire's in particular changes between runs. Worth doing when the shapes settle; not a
hackathon-morning change.

### `js-mng-loopback-url` (HIGH) — `frontend/src/services/api.ts`

```ts
const DEFAULT_API_URL = import.meta.env.DEV ? 'http://localhost:8000' : ''
```

The loopback address is already behind `import.meta.env.DEV`, so it cannot reach a build, and the
deployed dashboard is served by the backend on the same origin — hence the empty string. The
override the rule asks for exists: `VITE_API_URL`. This is the remediation, written as a dev
default rather than a required variable.

### `js-no-error-handling-async` (HIGH ×3) — `frontend/src/services/api.ts`

The shared `request` helper throws on purpose. Swallowing errors in the client would be the bug: the
dashboard has to show a panel as unavailable rather than as empty. Every caller handles it — each
hook in `frontend/src/hooks/` wraps its call in `try/catch` or `.catch()` and sets its own error
state. Catching here as well would hide the failures the hooks are built to report.

### `js-fetch-no-timeout` (MEDIUM ×3) — `frontend/src/services/api.ts`

A real gap, and the most tempting thing on this list to fix: an `AbortSignal.timeout()` in the
shared helper is four lines. It was left alone because those four lines sit in front of *every*
backend call the demo makes, including the route requests, and there was no time to exercise the
whole run afterwards. A timeout that fires early on a slow route lookup breaks the demo in exactly
the moment it is meant to protect. First thing to pick up after the submission.

## What remains

- `vite-missing-csp` — as a response header from `serve_dashboard`, report-only first.
- `js-fetch-no-timeout` — `AbortSignal.timeout()` in `request`, with the route calls given a longer
  deadline than the polling ones.
- `fa-mng-dict-response` — worth doing for the live endpoints once Deepfire's shapes settle.
- **The reset button swallows a failure** (`js-no-error-handling-async`, `App.tsx` and
  `hooks/useTriage.ts`). `resetDemo()` is awaited with nothing catching it and is wired straight to
  `onClick`. If the backend is down during a rehearsal reset the click silently does nothing and
  logs an unhandled rejection. Worth a `try/catch` that puts the failure on screen — left alone
  today because showing it properly is a UI change, not a lint fix.
- `js-empty-catch-block` ×3 (`ui/i18n.tsx`, `hooks/useClosures.ts`) — the intent is right and
  commented (keep the last list; `localStorage` is blocked in private mode), but a `console.debug`
  would make the swallow visible on stage and satisfy the rule.
- The frontend sweep ran with `coverage.reduced: true` throughout, and `backend/tests/` and the
  `voice/` packages were not scanned at all.
- `register_applied_actions` could not write the audit trail: it fails with
  `{"status": "failed", "reason": "unlinked"}` for the same reason as the full scan. The fixes are
  recorded here and in the commit on `norma-pass` instead. Importing the repository in the Norma
  portal would unlock both the full scan and the audit trail.

## Sources

- Norma MCP server, `https://api.qualityclouds.ai/mcp` — `live_check`, `link_repository`,
  `register_applied_actions`
- https://github.com/qualityclouds/norma-mcp
- `docs/services/norma.md`
