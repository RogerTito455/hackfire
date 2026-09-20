# Norma (QualityClouds): what we fixed, what we did not, and why

HackFire's answer to the Norma track. It lists every finding we acted on, every finding we left
alone, and the reason for each decision. The full finding-by-finding record, with the before/after
counts per file, is in [`docs/findings/2026-09-20-norma-scan.md`](docs/findings/2026-09-20-norma-scan.md);
this page is the summary a reviewer can read in five minutes.

Every fix carries an in-code marker — `Recommended by Norma — fixed with Claude Opus 5 via Claude Code`
— and the commits carry `Fixed-by: Norma MCP`, `LLM:` and `IDE:` trailers. Every finding we did not
fix carries a comment naming the rule and the reason, next to the code that triggers it. Both are
greppable:

```bash
grep -rn "Recommended by Norma" --include="*.ts" --include="*.tsx" --include="*.py" --include="*.js" .   # 23 fixes
grep -rn "Norma [a-z-]" --include="*.ts" --include="*.tsx" --include="*.py" . | grep -v Recommended       # 45 justifications
```

## How the code was scanned

Two ways, because one was not available:

- **The full portal scan**: the repository was imported into the QualityClouds portal by hand and
  scanned there — **148 findings**, worked through in batches.
- **`live_check` through the Norma MCP server**, one call per file, for the before/after delta.
  This was needed because `link_repository` answers `auto_import_not_available` for this private
  repository from inside the editor, which also blocks `get_open_issues` and
  `register_applied_actions`. `live_check` works unlinked and is deterministic, so the counts
  before and after a change are comparable.

On the eight core files measured both before and after, findings at medium and above went from
**44 to 41**, and security findings from **3 to 1** — and that last one is the CSP, which is now
sent (see below), though the rule still matches because it reads the HTML file, not the response.

## 1. What we fixed

### Security

| Rule | Sev | Where | What changed |
|---|---|---|---|
| `py-sec-xml-xxe` | HIGH | `backend/app/providers/dgt.py` | The DGT's public DATEX II feed is ~3 MB of third-party XML re-fetched every five minutes, parsed with the standard library, which expands internal entities. It now goes through `defusedxml`; a refused document raises the same `ValueError` the callers expect, so the feed degrades to "unavailable" instead of taking the process down. A test feeds it an external-entity document and an entity bomb. |
| `vite-missing-csp` | HIGH | `backend/app/main.py` | The dashboard now sends a real `Content-Security-Policy` **response header** (`content_security_policy()` + the `security_headers` middleware), not a meta tag: a meta tag cannot carry `frame-ancestors`, leaves the built assets uncovered and never reaches the tile-cache service worker. No `'unsafe-inline'`, no `'unsafe-eval'`, and a test asserts that. Exercised in Chromium across replay, live, the landing page and a real voice call: zero violations. |
| `vite-missing-referrer-policy` | MED | `frontend/index.html` | The dashboard's URLs carry resident, rescue and room identifiers, and it loads tiles, LiveKit and Vonage cross-origin, so the full path was leaking as the `Referer`. |

### Reliability — failures that were invisible or fatal

| Rule | Sev | Where | What changed |
|---|---|---|---|
| `js-no-error-handling-async` | HIGH | `frontend/src/hooks/useTriage.ts`, `frontend/src/App.tsx` | **The Reset button.** `resetDemo()` was awaited with nothing catching it and wired straight to `onClick`: a rehearsal reset against a backend that was down did nothing, silently, and logged an unhandled rejection. It now reports through `online`, the error state the hook already owns and the connection pill already shows. |
| `js-fetch-no-timeout` | MED | `frontend/src/services/api.ts` | **A timeout on every backend call.** A backend that accepts the connection and then never answers used to hang the panel that asked it, with nothing on screen, because the hooks only show their unavailable state when a call *fails*. One helper, one constant; the timeout arrives as the same `Error` a non-2xx does. Ten seconds was measured against the slowest endpoint (`/api/status/providers`, 4.3 s). |
| `js-fetch-no-timeout` | MED | `frontend/public/tile-cache-sw.js` | The tile request is bounded at 8 s, so a venue network that stalls cannot leave the map waiting. |
| `js-empty-catch-block` | HIGH | `frontend/public/tile-cache-sw.js` | `cache.put` was awaited inside `event.respondWith`, so a full or blocked cache (quota, private mode) rejected the whole response and the tile never reached the map **although the fetch had succeeded**. Storing is now best effort and the detached `trim()` has a catch. |
| `js-empty-catch-block` | HIGH | `frontend/src/ui/i18n.tsx`, `hooks/useClosures.ts`, `hooks/useAutopilot.ts` | Three empty catches kept their behaviour, which was right, and now log at `debug` level so the swallow is visible. Debug and not error: two of them run on a poll, and the connection pill already says the backend is down. |
| `js-no-error-handling-async` | HIGH | `video/scripts/audio.ts` | An unhandled top-level await: any failure came out as a stack trace. One line and exit 1 instead. |
| `py-mng-sys-exit-lib` | MED | `backend/app/pipelines/common.py` | `write_or_compare` called `sys.exit(1)` from a helper. It raises `OutputDiffers`, and each pipeline's `__main__` turns that into exit code 1 — same behaviour at the terminal, no process kill for a future importer. |

### Maintainability

| Rule | Sev | Where | What changed |
|---|---|---|---|
| `Magic-number timeout` | LOW | `pipelines/fetch_hotspots.py`, `fetch_zones.py`, `check_routes.py`, `providers/galtea.py` | Four magic-number timeouts became named constants, each with a line saying what the wait is for (Deepfire runs on shared capacity; Overpass is slow under load; a cold Railway container wakes first). |
| `open() without explicit encoding` | LOW | `video/scripts/export_map.py` | Six `read_text` calls pass `encoding="utf-8"`, so a machine whose locale is not UTF-8 reads the cached files the same way. |
| `js-nested-ternary` | MED | `frontend/src/ui/CrewPlanPanel.tsx` | A four-deep ternary inside JSX became four named cases read in order: no route, no forecast, in time by that margin, late by it. |
| `js-nested-ternary` | MED | `video/src/Scenes.tsx` ×3 | Chains of ternaries on an index became colour tables in the order of the rows they colour. |
| `fa-mnt-no-typing-param` | MED | `backend/app/main.py` | The `request_locale` middleware's `call_next` and return are annotated. No runtime change. |

## 2. What we did not fix

Each of these has a comment at the exact line, naming the rule and the reason.

| Rule | Sev | × | Where |
|---|---|---|---|
| `py-maint-no-print` | MED | the bulk of 26 | `backend/app/pipelines/` (10 modules) |
| `js-no-error-handling-async` | HIGH | 15 | `services/videoCall.ts`, `services/voiceSession.ts`, `services/api.ts`, `video/scripts/audio.ts` |
| `fa-mng-no-status-code` | MED | 19 | `backend/app/main.py` |
| `fa-mng-dict-response` | MED | 12 | `backend/app/main.py` and three `@cached` loaders |
| `fa-scl-no-pagination` | HIGH | 7 | `backend/app/main.py` |
| `fa-scl-global-state` | HIGH | 2 (+15 `global`) | `impact.py`, and the module-level caches in `live.py`, `live_spread.py`, `live_dgt.py`, `scenario.py`, `crew_room.py`, `providers/deepfire.py`, `autopilot.py` |
| `rct-prf-setstate-in-useeffect` | HIGH | 6 | `TriageMap.tsx`, `BottomSheet.tsx`, `usePlayhead.ts` ×2, `useCrewRoom.ts`, `useResidentCamera.ts` |
| `rct-unsafe-href-binding` | HIGH | 5 | `landing/Landing.tsx` ×3, `ActivityLog.tsx`, `RescueQueue.tsx` |
| `js-nested-ternary` | MED | 5 | `OrdersPanel.tsx` ×2, `TriageMap.tsx`, `main.tsx`, `LiveStatus.tsx` |
| `js-inner-html-assignment` | HIGH | 3 | `TriageMap.tsx` |
| `rct-dangerous-inner-html` | HIGH | 1 | `Icon.tsx` |
| `js-function-in-loop` | MED | 1 | `TriageMap.tsx` |
| `js-mng-loopback-url` | HIGH | 1 | `services/api.ts` |

## 3. Why

**The rule matched something that is not what it is looking for.** Most of the list above.

- `py-maint-no-print` fires inside `backend/app/pipelines/`, which are **terminal commands**, not
  request-path code: `pnpm check:routes` prints `OK:` / `NOT OK:` and that verdict *is* the
  command's interface. Routing it through `logging` would make the tools quieter, not more
  observable. The request path uses `logging.getLogger(...)` throughout and scans clean. The
  reasoning is written once in the package docstring.
- `fa-scl-global-state` in `impact.py` is a plain false positive: the flagged `polygons` is a local
  variable inside a `@cached` function.
- `fa-mng-dict-response` and `fa-mnt-no-typing-param` outside `main.py` matched `@cached` loaders and
  a pydantic validator with no route decorator at all — the FastAPI ruleset keying on `-> dict[...]`
  under any decorator.
- `rct-prf-setstate-in-useeffect`: in all six places the `setState` is **not** in the effect body —
  it is inside a `ResizeObserver` callback, a MapLibre `load` handler, a `requestAnimationFrame`
  callback or the continuation of an async IIFE. A height or a map is only known after layout.
- `rct-unsafe-href-binding`: the three on the landing page bind the literal `'/'` declared in
  `src/landing.tsx`; `ActivityLog`'s is our own same-origin `/api/audit/export` path; `RescueQueue`'s
  is written by our backend from `HACKFIRE_PUBLIC_URL` and an id it generated. No user or
  third-party value reaches any of them. We tried the "sanitise every href" version and reverted it:
  it added a helper that could only ever return its input.
- `js-inner-html-assignment` / `rct-dangerous-inner-html`: every one takes a hand-written SVG string
  from `ui/markers.ts` or one of our own files in `ui/icons/` — fixed markup, a colour from
  `theme.ts`, an icon name from a closed union. A MapLibre `Marker` needs a real DOM node, so JSX is
  not an option there. The one value that comes from the registry, a resident's name, goes through
  `setAttribute` and `Popup.setText`, which escape it.
- `js-mng-loopback-url`: the loopback address is behind `import.meta.env.DEV`, so no build carries
  it, and `VITE_API_URL` is the override the rule asks for.

**The rejection is the contract.** The 15 `js-no-error-handling-async` in `services/` are awaits that
propagate on purpose: `api.ts` names the path and throws, and each caller — `useTriage`,
`useClosures`, `useCrewPlan`, `useResidentCamera` — decides what to show, because the dashboard polls
a dozen endpoints every few seconds and a single shared handler would either spam the console or
swallow the one failure that matters. Catching them at the source would make the failure *less*
visible, not more.

**It is the architecture, and changing it is out of scope.** The fifteen `global` statements are
module-level caches of a last good answer (Deepfire's fires, its simulations, the DGT feed, the
active scenario), each behind a `Lock` or `RLock`, each with a reset next to it. This is
CLAUDE.md's "demo mode comes first": one process, everything slow cached as a static file, because
the live demo must not depend on a third-party API answering in time. Norma's remediation is "move
it to Redis", which is a different product.

**It is a real point we are choosing not to spend the deadline on.** `fa-scl-no-pagination` (7) and
`fa-mng-no-status-code` (19) in `main.py` are fair: the dashboard API returns whole collections and
leans on FastAPI's default status codes. The collections are a five-to-ten-household registry and a
day of cached hotspots — bounded by the demo, not by a database — and the response models are the
contract the voice agents and the dashboard share ([`models.py`](backend/app/models.py)). Paginating
them would change that contract for every caller, hours before a feature freeze, to fix a problem
this deployment cannot have. It is the first thing to do if the project continues.

**Two of them we tried and reverted.** A second pass by a teammate re-fixed several of these
independently — safe-href helpers, `replaceChildren` instead of `innerHTML`, a meta CSP with a
dev-server plugin. We kept the versions that were verified end to end on the real demo phone and
against the live CSP, and dropped the duplicates rather than carry two answers to the same finding
([PR #84](https://github.com/RogerTito455/hackfire/pull/84)).

## What Norma changed about how we work

Three of the fixes were bugs a reviewer would have wanted found: the Reset button that did nothing
when the backend was down, the tile cache that threw away a tile it had already fetched, and every
backend call being able to hang forever. None of them would have shown up in a test — they only
appear when something else is already failing, which is exactly the situation a demo hits on stage.
