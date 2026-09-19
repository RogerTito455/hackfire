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

```
backend/app/main.py     FastAPI app: dashboard API (/api) and agent tools (/tools)
backend/app/models.py   Pydantic models; the tool contract lives here
backend/app/state.py    In-memory triage state and rescue prioritisation
backend/tests/          pytest
frontend/src/App.tsx    Coordinator dashboard (MapLibre GL)
frontend/src/api.ts     Typed backend client
data/                   Static demo data (registry, cached hotspots and spread)
scripts/                One-off data downloads
```

## Commands

```bash
cd backend && uv sync && uv run uvicorn app.main:app --reload   # http://localhost:8000, docs at /docs
cd backend && uv run pytest
cd frontend && npm install && npm run dev                       # http://localhost:5173
cd frontend && npm run build                                    # type-checks, then bundles
```

Run `uv run pytest` and `npm run build` before every commit that touches the respective side.

## Conventions

- **The tool contract is shared.** The five `/tools` endpoints are the interface between the voice track and everything else. Changing a request or response model in `models.py` means updating `frontend/src/api.ts` and telling the team.
- **Stubs are explicit.** Placeholder responses set `stub: true` and carry a `TODO(track)` comment, where track is `map`, `voice` or `data`. Remove both when the real implementation lands.
- **Demo mode comes first.** Everything slow or external (Deepfire, the spread simulation, Overpass) is fetched once and cached as static files under `data/`. The live demo must not depend on a third-party API answering in time. Deepfire runs on shared capacity and returns 503 under load.
- **Routing limits.** openrouteservice rejects `avoid_polygons` larger than 200 km² or 20 km across. Always clip the fire polygon to the demo box `-4.85,40.30,-4.40,40.50` or tighter.
- **MapLibre GL v6 has no default export.** Use named imports (`import { Map as MapLibreMap, Marker } from 'maplibre-gl'`).

## Secrets and personal data

- Keys live in `.env` (git-ignored). Never commit them; add new ones to `.env.example` with an empty value.
- `data/neighbors.local.json` holds the team's real phone numbers and is git-ignored. `Neighbor.phone` is excluded from serialisation on purpose; do not expose it through the API.
- `NOTES.internal.md` is git-ignored team material. Do not copy its contents into tracked files.

## Tone

The replay is a real fire from July 2026 in which people lost their homes. No invented counterfactuals ("we would have saved…", "N hours before 112"). The only headline number is *lead time*, computed from satellite hotspots. Check any press figure against its source before it goes into the README, the UI or a slide.
