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

**Superseded: done in the portal pass below**, once there was time to exercise the whole run after
it. The reasoning for leaving it that morning stands as written:

A real gap, and the most tempting thing on this list to fix: an `AbortSignal.timeout()` in the
shared helper is four lines. It was left alone because those four lines sit in front of *every*
backend call the demo makes, including the route requests, and there was no time to exercise the
whole run afterwards. A timeout that fires early on a slow route lookup breaks the demo in exactly
the moment it is meant to protect. First thing to pick up after the submission.

## What remains

- `vite-missing-csp` — as a response header from `serve_dashboard`, report-only first.
- ~~`js-fetch-no-timeout`~~ — **done** in the portal pass below. One deadline for every call in the
  end, not two: the slowest endpoint we have is bounded well inside it.
- `fa-mng-dict-response` — worth doing for the live endpoints once Deepfire's shapes settle.
- ~~**The reset button swallows a failure**~~ — **done** in the portal pass below, through the
  connection pill rather than new UI. As it read that morning:
  (`js-no-error-handling-async`, `App.tsx` and
  `hooks/useTriage.ts`). `resetDemo()` is awaited with nothing catching it and is wired straight to
  `onClick`. If the backend is down during a rehearsal reset the click silently does nothing and
  logs an unhandled rejection. Worth a `try/catch` that puts the failure on screen — left alone
  today because showing it properly is a UI change, not a lint fix.
- ~~`js-empty-catch-block` ×3~~ — **done** in the portal pass below, with exactly the `console.debug`
  this bullet proposed.
- The frontend sweep ran with `coverage.reduced: true` throughout, and `backend/tests/` and the
  `voice/` packages were not scanned at all.
- `register_applied_actions` could not write the audit trail: it fails with
  `{"status": "failed", "reason": "unlinked"}` for the same reason as the full scan. The fixes are
  recorded here and in the commit on `norma-pass` instead. Importing the repository in the Norma
  portal would unlock both the full scan and the audit trail.

## Full-scan batches 1–20 and 21–40 from the portal

The repository was later imported into the QualityClouds portal by hand, and the full scan that
`link_repository` could not start from the MCP server ran there: **148 findings**. This section
covers the first two batches handed back to us, 1–40, judged one by one against the code rather
than by rule name. The line numbers below are the scan's; several had already moved.

Each fix carries the comment `Recommended by Norma — fixed with Claude Opus 5 via Claude Code`
next to the change, and each accepted finding carries `Norma <rule>: <why it is safe here>` where
the rule fires, so the reasoning is in the code and not only here.

Two findings in these batches are handled elsewhere and were not touched:

- `backend/app/providers/dgt.py:127` (`py-sec-xml-xxe`) — **already fixed on main** by #74, the
  `defusedxml` change written up above. Nothing to do.
- `frontend/index.html:3` (`vite-missing-csp`) — **left alone on purpose.** It is being added as a
  response header from the backend, which is where the section *What was accepted* argues it
  belongs. Editing the entry point would collide with that work.

### Fixed (6)

| Finding | Rule | What was wrong |
|---|---|---|
| `frontend/src/hooks/useTriage.ts:55` + `App.tsx:53` | `js-no-error-handling-async` | The reset button. |
| `frontend/src/ui/i18n.tsx:42` | `js-empty-catch-block` | A refused `localStorage` write vanished. |
| `frontend/src/hooks/useClosures.ts:30` | `js-empty-catch-block` | A failed closures poll vanished. |
| `frontend/src/hooks/useAutopilot.ts:26` | `js-empty-catch-block` | A failed autopilot read vanished. |
| `frontend/public/tile-cache-sw.js:15`, `:27` | `js-no-error-handling-async` | A full tile cache broke the map. |
| `video/scripts/audio.ts:154`, `:208` | `js-no-error-handling-async` | An unhandled rejection at the top level. |

**The reset button** was the one real user-visible gap, and yesterday's pass had already listed it
under *What remains*. `resetDemo()` was awaited in `useTriage.reset` with nothing catching it, and
`App.tsx` awaited that in turn straight from `onClick`: with the backend down, a rehearsal reset
silently did nothing and logged an unhandled rejection. `reset` now catches, logs with
`console.error` and sets `online` to false — the error state the hook already owns and the
connection pill already shows — then refreshes, which clears it as soon as the backend answers
again. No new UI, and `App.tsx`'s `resetDemo` can no longer reject, which is what the `App.tsx:53`
finding was about.

**The three empty catches** each hid a failure that the operator had no way to see: the language
that was not remembered (`localStorage` refused in private mode), a closures poll that did not
answer, and the autopilot state that could not be read. All three keep exactly the behaviour they
had — the intent was right — and now log the error at **debug** level. Debug rather than error on
purpose: the closures catch runs every `POLL_MS` and the autopilot one on every refresh, so error
level would fill the console during any offline moment on stage while the connection pill is
already saying it. The swallow is now visible to anyone who looks.

**The tile cache service worker** (#13) had the one latent bug in the batch. `cache.put` was
awaited inside the promise handed to `event.respondWith`, so a `QuotaExceededError` — a full or
blocked cache, which is exactly what a venue laptop in private mode gives you — rejected the whole
response and the tile never reached the map, although the fetch had succeeded. Storing is now best
effort inside its own `try/catch`, and the detached `trim(cache)` has a `.catch`, so neither can
take a tile down with it. The tile still comes back on a failed write; only the caching is lost.

**`video/scripts/audio.ts`** is the ElevenLabs generator behind `pnpm video:voice`, `video:sfx` and
`video:music`. Its top-level `await command()` had no handler, so any failure — no key, a 4xx from
ElevenLabs, ffmpeg missing — came out as an unhandled rejection's stack trace. It now prints one
line and exits 1. The `:154` finding inside `sfx()` is *accepted*: `call()` throwing is how one bad
sound stops the run instead of writing a truncated mp3, and the new handler at the bottom is where
it lands.

### Accepted (the rest)

Every one of these was traced to where its value comes from. Several were already analysed in
yesterday's `live_check` pass; the reasoning now also sits in the code.

**`rct-unsafe-href-binding` (HIGH ×5)** — `Landing.tsx` ×3, `ActivityLog.tsx:39`,
`RescueQueue.tsx:63`. None of the three sources is user input:

- `Landing.tsx`'s `demoUrl` is the literal `'/'` declared in `src/landing.tsx`, the only place the
  component is mounted.
- `ActivityLog.tsx`'s `downloadUrl` is `auditDownloadUrl()` in `services/api.ts`: our own
  same-origin `/api/audit/export` path with the locale `encodeURIComponent`'d.
- `RescueQueue.tsx`'s `link.link` is written by the backend in `rescue_video.py` as
  `{public_url}/v/{link id}` — the deployment's own `HACKFIRE_PUBLIC_URL` and an id it generated.
  A resident can neither choose nor influence it.

**`js-inner-html-assignment` (HIGH ×3) and `rct-dangerous-inner-html` (HIGH ×1)** —
`TriageMap.tsx:765`, `:795`, `:819` and `Icon.tsx:66`. All four take **our own hand-written SVG**:
the map markers come from `ui/markers.ts`, which concatenates fixed markup with a colour from
`theme.ts` and an icon name from a closed union, and `Icon.tsx` renders a file from `ui/icons/`,
bundled at build time and validated by `scripts/check-icons.mjs`. No user or network content
reaches either. The one registry value on a marker, the resident's name, goes through
`setAttribute` and `Popup.setText`, which escape. MapLibre markers need real DOM nodes, so JSX is
not an option, and DOMPurify for static markup would add the dependency CLAUDE.md rules out.

**`rct-prf-setstate-in-useeffect` (HIGH ×10)** — `TriageMap.tsx:648`, `useCrewRoom.ts:68` and
`:70`, `BottomSheet.tsx:46`, `usePlayhead.ts:17`, `:20` and `:46`, `useResidentCamera.ts:28` and
`:35`. The rule's own semgrep pattern excludes `.then`, `.catch`, `setTimeout`, `addEventListener`
and a few others, but not the four shapes this codebase uses, which is why they all match:

- MapLibre's `load` callback (`TriageMap.tsx`) — the style is ready when the map says so.
- an async IIFE's continuation and its `catch` (`useCrewRoom.ts`, `useResidentCamera.ts`) — joining
  a room or opening a single-use link is a network round trip; the outcome cannot be derived during
  render, and a `useRef` guard keeps each to one run.
- a `ResizeObserver` callback (`BottomSheet.tsx`) — a height is only known after layout. This
  component is the one that genuinely needed the adjust-during-render pattern, and it already uses
  it, a few lines below the flagged effect.
- an `IntersectionObserver` and a `requestAnimationFrame` callback (`usePlayhead.ts`).

The single call that really is in an effect body is `usePlayhead.ts:17`, the fallback for a browser
with no `IntersectionObserver` or a ref that never attached. Both deps are stable, so it runs at
most once: there is no second render pass per change to remove, and it cannot be derived during
render because it depends on `ref.current`.

**`js-no-error-handling-async` (HIGH ×10)** — `services/api.ts:119` and `:138`,
`services/videoCall.ts:11`, `:20`, `:42`, `:75`, `:85`, `:102`, `services/voiceSession.ts:15` and
`:34`. This is the deliberate boundary described above: `services/` throws, `hooks/` catches.
`joinVideo` and `reopenRoad` reject into `useResidentCamera` and `useClosures.reopen`; every entry
point in `videoCall.ts` rejects into `useResidentCamera`, `useRescueVideo` or `useCrewRoom`; and
`joinConversation` rejects into `useConversation.start`. Each of those hooks awaits inside a
`try/catch` and moves its own state to `'error'`, which is what the dashboard renders. Catching in
`services/` as well would swallow the transition the hooks exist to report. `voiceSession.ts` shows
where a handler *is* right: a refused microphone is caught so the room is left before the error
goes up.

**`js-mng-loopback-url` (HIGH)** — `services/api.ts:24`, unchanged and now commented in place: the
loopback address is behind `import.meta.env.DEV`, so no build can carry it, and `VITE_API_URL` is
the override the rule asks for.

### Checked after the change

`pnpm check` passes (backend tests, icons, locales, frontend build). The backend was then run with
the built dashboard on one port and driven in a browser: replay mode draws the five resident pins,
the autopilot switch turns on and off and the triage state follows it, live mode loads the fires,
and the console stays clean.

### The later batches: what else landed in these files

More of the 148 came back while the pass was open (batches 61–148, mostly backend and video, taken
by someone else). These are the ones in the files above.

**Fixed — a timeout on every backend call** (`js-fetch-no-timeout`, MEDIUM, `services/api.ts:36`,
`:119`, `:138`). Yesterday's pass left this one and said why; with the whole run exercisable
afterwards, it is now done. A backend that accepts the connection and then never answers used to
hang the panel that asked, showing nothing: the hooks only reach their unavailable state when a
call *fails*. A single `fetchApi` helper now carries `AbortSignal.timeout(REQUEST_TIMEOUT_MS)` —
one named constant, **10 s** — and converts the `TimeoutError` into the same kind of `Error` a
non-2xx already throws, so every hook's existing `catch` covers it with no new UI. The three
entry points that bypassed `request()` (`joinVideo`, `reopenRoad`) go through it too.

Ten seconds was measured, not guessed. The slowest endpoint in the dashboard is
`/api/status/providers` at ~4.3 s, and it is itself bounded — `provider_status.TIMEOUT_S` is 4 s per
provider with an overall wait. `/api/live/spread` is 1.7 s, `/api/live/fires` 0.55 s, everything
else milliseconds. The demo's routes are all cached (`pnpm check:routes`), so no route lookup goes
to openrouteservice during the demo. That leaves better than twice the margin on the worst case,
which is why one deadline was enough and the two-tier scheme the earlier note imagined was not
needed.

Proved in the browser rather than argued: holding `/api/closures` open for 30 s, the call gives up
at exactly 10 s with `/api/closures did not answer in 10000 ms`, `useClosures` catches it, the rest
of the dashboard keeps drawing, and there is no unhandled rejection.

**Fixed — a timeout on a tile fetch** (`js-fetch-no-timeout`, MEDIUM, `tile-cache-sw.js:25`).
`TILE_TIMEOUT_MS`, 8 s, on the one request the worker makes to the tile host. The cache is
consulted first, so everything already shown keeps working on a stalled network; this only bounds
the trip for a tile that is not cached yet. The service worker still filled its cache normally in
the browser check (138 tiles).

**Fixed — one nested ternary** (`js-nested-ternary`, MEDIUM, `ui/CrewPlanPanel.tsx:56`, `:58`). The
verdict line for a crew's stop was a four-deep ternary inside JSX. It is now a `verdictText(step)`
with four early returns, in the order a reader needs them: no route, no forecast, in time by that
margin, late by it. Identical output — the panel still renders *“Sale ya · llega en 10 min / 3 h
41 min antes que el fuego”* in the browser check.

**Accepted — the other six nested ternaries.** `OrdersPanel.tsx:82` and `:106`, `LiveStatus.tsx:19`,
`TriageMap.tsx:858` and `main.tsx:20` are each one value with three cases, on one line, next to what
they label: a safe point's tag, a button's label, a locale key, a caption, and the route table.
Hoisting any of them into a helper moves the decision away from the thing it decides without making
it shorter, and these five render the demo. Each carries its reasoning.

**Accepted — `js-function-in-loop`** (MEDIUM, `TriageMap.tsx:824`). One click handler per resident
is the point: each closes over its own neighbour's id. It is created only when that marker is
rebuilt, not on every pass, and it reads `onSelect.current`, so the closure never goes stale.

**Accepted — `js-maint-no-console`** (`scripts/check-locales.mjs:115`, `check-icons.mjs:361`). Both
are `pnpm check` commands whose output *is* their interface — the verdict a developer and CI read,
the same argument as `py-maint-no-print` in `backend/app/pipelines/` above.

**Already fixed on main:** `frontend/index.html:2` (missing Referrer-Policy) by #74, written up
under *What was fixed*. Nothing to do.

**`Landing.tsx:64`** is the third `href={demoUrl}` on that page and got the same comment as the
other two in this pass.

## Sources

- Norma MCP server, `https://api.qualityclouds.ai/mcp` — `live_check`, `link_repository`,
  `register_applied_actions`
- https://github.com/qualityclouds/norma-mcp
- `docs/services/norma.md`
