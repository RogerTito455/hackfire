# HackFire

Hackathon project (HackBarna 2026). A voice agent calls residents ahead of a wildfire, gives them an evacuation route and triages them for the emergency coordinator. **Read [PLAN.md](PLAN.md) first**: it is the source of truth for scope, stack, schedule and decisions.

## Hard deadlines

- Saturday 21:00 — feature freeze.
- Sunday 11:00 — code submission. Sunday morning is for rehearsal and bug fixes only.

## Scope guardrail

The core is the four steps in PLAN.md section 3. Before building anything, check it against section 4. If a request falls under "Extensions" or "Out", say so and ask before starting. Extensions are ordered Norma → Vonage → Devin and only begin once the core works end to end.

## Language

Everything written into this repo is in **English**: docs, code, comments, commit messages, issues and pull requests. The team chats in Spanish; reply to them in Spanish.

## Layout

Monorepo: pnpm workspace for the frontend, uv project for the backend, root `package.json` scripts for everything.

```
backend/app/main.py        FastAPI app: dashboard API (/api) and agent tools (/tools)
backend/app/models.py      Pydantic models; the tool contract lives here
backend/app/state.py       In-memory triage state and rescue prioritisation
backend/app/config.py      Every key, URL and path, read from the environment
backend/app/providers/     One module per external service (deepfire, routing, llm, voice)
backend/app/pipelines/     One-off data downloads that write to data/
backend/tests/             pytest
frontend/src/domain/       Types and pure functions — no React, no fetch, no styling
frontend/src/services/     Backend client — the only place that knows URLs and HTTP
frontend/src/hooks/        State and polling; returns plain data
frontend/src/ui/           Presentational components, theme.ts, CSS
frontend/src/App.tsx       Composition root only: hook → UI
voice/                     Unmute packages for the SLNG voice agents; `unmute validate` inside each
data/                      Static demo data (registry, cached hotspots and spread)
docs/                      Setup, one page per service, workflow, findings log. Update it as you go
```

## Commands

```bash
pnpm bootstrap       # pnpm install + uv sync (never `pnpm setup`: it is a pnpm built-in)
pnpm dev:api         # http://localhost:8000, docs at /docs
pnpm dev:web         # http://localhost:5173
pnpm check           # backend tests, then frontend type-check and build
pnpm data:hotspots   # download Deepfire hotspots into data/
```

Run `pnpm check` before every commit.

## Conventions

- **Never hand-write manifests or config JSON.** `package.json`, `pyproject.toml`, lockfiles and tsconfig changes go through commands: `pnpm add`, `pnpm pkg set`, `uv add`, `uv remove`. pnpm only — no npm, no yarn.
- **UI is independent of logic.** Components in `frontend/src/ui/` take props and render; they never fetch, poll or import from `services/`. Logic lives in `domain/` (pure) and `hooks/` (stateful). Colours and labels live in `ui/theme.ts` and CSS variables in `ui/theme.css`. A redesign should touch `ui/` only.
- **No component kits or icon packages.** No shadcn, no icon or SVG libraries. Plain CSS and hand-written markup. MapLibre GL is the single third-party UI dependency.
- **Third parties go through `providers/`.** Nothing outside `backend/app/providers/` makes HTTP calls to an external service, and nothing outside `config.py` reads `os.environ`.
- **The tool contract is shared.** The five `/tools` endpoints are the interface between the voice track and everything else. Changing a request or response model in `models.py` means updating `frontend/src/domain/triage.ts` and telling the team.
- **Stubs are explicit.** Placeholder responses set `stub: true` and carry a `TODO(track)` comment, where track is `map`, `voice` or `data`. Remove both when the real implementation lands.
- **Demo mode comes first.** Everything slow or external (Deepfire, the spread simulation, Overpass) is fetched once and cached as static files under `data/`. The live demo must not depend on a third-party API answering in time. Deepfire runs on shared capacity and returns 503 under load.
- **Routing limits.** openrouteservice rejects `avoid_polygons` larger than 200 km² or 20 km in height or width. The demo box `-4.85,40.30,-4.40,40.50` is ~38 × 22 km, so clipping to it is not enough: clip the fire to a square of at most 14 km around the route (see `docs/findings/2026-09-19-ors-avoid-polygon-limit.md`).
- **MapLibre GL v6 has no default export.** Use named imports (`import { Map as MapLibreMap, Marker } from 'maplibre-gl'`).

## Secrets and personal data

- Keys live in `.env` (git-ignored). Never commit them; add new ones to `.env.example` with an empty value.
- `data/neighbors.local.json` holds the team's real phone numbers and is git-ignored. `Neighbor.phone` is excluded from serialisation on purpose; do not expose it through the API.
- `NOTES.internal.md` is git-ignored team material. Do not copy its contents into tracked files.

## Tone

The replay is a real fire from July 2026 in which people lost their homes. No invented counterfactuals ("we would have saved…", "N hours before 112"). The only headline number is *lead time*, computed from satellite hotspots. Check any press figure against its source before it goes into the README, the UI or a slide.
