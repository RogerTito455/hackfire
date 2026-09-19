# HackFire

**A voice agent that calls residents before a wildfire reaches them, tells them how to get out, and shows the emergency coordinator who needs rescue.**

Built at [HackBarna 2026](https://www.hackbarna.com/en/events/aisummit26) (19–20 September, Norrsken House Barcelona) for the Norrsken / Deepfire "AI for Wildfire" challenge, track 4: *values at risk*.

> Every resident who evacuates on their own is a rescue the firefighters don't have to make.

## The problem

On 23 July 2026 the Burgohondo wildfire in Ávila, the largest in Spain, ran 3 km in 40 minutes and reached the La Atalaya housing estate. More than 1,200 people were evacuated from it and 5 homes were destroyed.

Public alerting today is one-way and impersonal. ES-Alert broadcasts the same message to a whole area and does not listen: the coordinator does not know who has left, who never got the message, and who cannot move. Rescues surface late, through saturated 112 lines, when crews are already committed.

## How it works

1. **The fire and where it is heading.** Deepfire satellite hotspots on a map with a time slider, and an hour-by-hour predicted spread. Live mode shows fires burning now; replay mode reproduces 23 July 2026.
2. **Who is in its path.** The predicted spread is intersected with towns, housing estates, care homes and roads from OpenStreetMap. Each zone gets a time to impact.
3. **The agent calls residents in the at-risk zones.** It gives each one a route out, on foot or by car, that avoids the predicted fire, and asks whether they can leave on their own, how many they are, and what they can see.
4. **Triage for the coordinator.** Each resident becomes *evacuating*, *no answer* or *needs rescue*. Rescues are ranked by time to impact, pushed to the fire crew, and can be queried by voice.

Calls are triggered by the prediction, hours ahead, while cell towers still work. "No answer" is a signal too: it tells the coordinator where to send a patrol.

## Status

Hackathon skeleton. What works today:

- Backend with the five agent tools, an in-memory triage state and a prioritised rescue queue. `report_status` and `get_rescue_queue` are real; fire status and routing return stubs marked `"stub": true`.
- Dashboard with a map of the demo area, resident pins coloured by triage state, live counts and the rescue queue, polling the backend every 2 seconds.

Still to build: hotspot and spread layers, time slider, routing, the voice agent and outbound calls, crew notifications. See [PLAN.md](PLAN.md) and the issues.

## Architecture

A single repo, run on localhost and deployed straight from `main`. No staging environment.

```
frontend/src/
  domain/      Types and pure functions. No React, no fetch, no styling
  services/    Backend client: the only place that knows URLs and HTTP
  hooks/       State and polling; returns plain data
  ui/          Presentational components, theme and CSS. Props in, markup out
backend/app/
  main.py      Dashboard API (/api) and agent tools (/tools)
  models.py    The tool contract
  state.py     Triage state and rescue prioritisation
  config.py    Every key, URL and path, read from the environment in one place
  providers/   One module per external service: Deepfire, openrouteservice, Nebius, SLNG
  pipelines/   One-off data downloads that write to data/
data/          Static demo data: resident registry, cached hotspots and spread
```

The UI is independent of the logic: redesigning the dashboard means touching `ui/` only. No component kit and no icon library; the one third-party UI dependency is MapLibre GL.

| Piece | Technology |
|---|---|
| Fire data and spread | [Deepfire API](https://docs.deepfire.co/llms.txt) |
| Voice, calls and SMS | [SLNG](https://docs.slng.ai/llms.txt) |
| LLM | [Nebius Token Factory](https://docs.tokenfactory.nebius.com/quickstart) |
| Routing | [openrouteservice](https://openrouteservice.org/) with `avoid_polygons` |
| Places at risk | OpenStreetMap via Overpass |

### Agent tool contract

The voice agent talks to the rest of the system through five HTTP tools under `/tools`:

| Tool | Purpose |
|---|---|
| `get_fire_status(zone)` | State of the fire front and time to impact for a zone |
| `get_evacuation_route(address, mode)` | Walking or driving route that avoids the predicted fire |
| `report_status(neighbor_id, status, people, mobility, observation)` | Record what the resident said; updates triage |
| `get_rescue_queue()` | Rescues ranked by priority |
| `get_rescue_route(rescue_id)` | Route for the fire crew |

Interactive docs are served at `http://localhost:8000/docs`.

## Running it locally

The full guide, with troubleshooting, is in [docs/setup/new-machine.md](docs/setup/new-machine.md). In short:

**1. Tools.** Git, Node 20+, pnpm 10, and [uv](https://docs.astral.sh/uv/) (it fetches Python 3.12 by itself). On Windows, use WSL2.

```bash
corepack enable                                    # pnpm, at the version pinned in package.json
curl -LsSf https://astral.sh/uv/install.sh | sh    # uv; open a new shell afterwards
```

**2. Clone and install.**

```bash
git clone https://github.com/RogerTito455/hackfire.git
cd hackfire
pnpm bootstrap  # frontend and backend dependencies (not `pnpm setup`, which is a pnpm built-in)
```

**3. Keys.** `cp .env.example .env` and fill in the keys you have; [docs/setup/environment.md](docs/setup/environment.md) says what each one unlocks. The skeleton runs without any of them.

**4. Run**, in two terminals:

```bash
pnpm dev:api    # backend  — http://localhost:8000
pnpm dev:web    # frontend — http://localhost:5173
```

To try the triage flow without the voice agent:

```bash
curl -X POST localhost:8000/tools/report_status \
  -H 'Content-Type: application/json' \
  -d '{"neighbor_id":"n02","status":"needs_rescue","people":2,"mobility":"cannot walk"}'
```

The pin for that resident turns red and they appear in the rescue queue. `POST /api/reset` restarts the demo.

### Tests

```bash
pnpm check      # backend tests, then frontend type-check and build
```

### Resident registry

`data/neighbors.sample.json` holds placeholder residents and is safe to commit. For the demo, copy it to `data/neighbors.local.json` (git-ignored) and put in real addresses and the team's own phone numbers. Phone numbers are never returned by the API.

## Documentation

[docs/](docs/README.md) holds everything beyond this page: setup, one page per external service (Deepfire, SLNG, Nebius, openrouteservice and the sponsor extensions), Claude Code with the project's MCP servers and skills, the development workflow, and a dated log of findings. [PLAN.md](PLAN.md) remains the source of truth for scope and decisions.

## A note on the real fire

The demo replays a real event from two months ago in which people lost their homes. Our headline figure, *lead time*, is computed from satellite data only: the gap between the moment the system flags a zone as at risk and the moment hotspots reach it. We make no claim about what the emergency services did or when.

## License

[MIT](LICENSE)
