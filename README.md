# HackFire

**A voice agent that calls residents before a wildfire reaches them, tells them how to get out, and shows the emergency coordinator who needs rescue.**

Built at [HackBarna 2026](https://www.hackbarna.com/en/events/aisummit26) (19–20 September, Norrsken House Barcelona) for the Norrsken / Deepfire "AI for Wildfire" challenge, track 4: *values at risk*.

> Every resident who evacuates on their own is a rescue the firefighters don't have to make.

## The problem

On 23 July 2026 the Burgohondo wildfire in Ávila ran 3 km in 40 minutes and reached the La Atalaya housing estate in El Tiemblo. Between 1,200 and 1,300 people were evacuated from it and 5 homes were destroyed ([sources](docs/findings/2026-09-19-press-figures.md)).

Public alerting today is one-way and impersonal. ES-Alert broadcasts the same message to a whole area and does not listen: the coordinator does not know who has left, who never got the message, and who cannot move. Rescues surface late, through saturated 112 lines, when crews are already committed.

## How it works

1. **The fire and where it is heading.** Deepfire satellite hotspots on a map with a time slider, and an hour-by-hour predicted spread. Live mode shows fires burning now; replay mode reproduces 23 July 2026.
2. **Who is in its path.** The predicted spread is intersected with towns, housing estates, care homes and roads from OpenStreetMap. Each zone gets a time to impact.
3. **The agent calls residents in the at-risk zones.** It gives each one a route out, on foot or by car, that avoids the predicted fire, and asks whether they can leave on their own, how many they are, and what they can see.
4. **Triage for the coordinator.** Each resident becomes *evacuating*, *no answer* or *needs rescue*. Rescues are ranked by time to impact, pushed to the fire crew, and can be queried by voice.

Calls are triggered by the prediction, hours ahead, while cell towers still work. "No answer" is a signal too: it tells the coordinator where to send a patrol.

## Status

Hackathon build, deployed at **https://frontend-production-ae2c.up.railway.app** (one Railway service; see [Deployment](docs/setup/deployment.md)). What works today:

- Backend with the five agent tools, an in-memory triage state and a prioritised rescue queue. All five tools are real: `report_status`, `get_rescue_queue`, `get_fire_status` and both routing tools.
- Dashboard with a map of the demo area, resident pins coloured by triage state, live counts and the rescue queue, polling the backend every 2 seconds.
- Replay of the fire: 7,068 Deepfire satellite hotspots from 22–24 July 2026, cached in `data/`, on a time slider with play and pause. Hotspots are coloured by age and sized by fire radiative power.
- Live mode: a toggle switches the map to Deepfire's active fire clusters right now, refreshed every minute. If Deepfire is down, the page shows a message and the replay keeps working.
- Predicted spread and zones at risk: for the replay of 23 July, a cone from the front's velocity gives a forecast every 30 minutes, drawn hour by hour on the map, and the panel lists the places in its path (La Atalaya, El Tiemblo, care homes, schools, health centres, roads) with their time to impact. `get_fire_status` answers from the same numbers, for the moment the slider is on.
- Lead time: La Atalaya is flagged 6 h 8 min before the first satellite hotspot comes within 3 km of it, computed from satellite data only ([how](docs/findings/2026-09-19-lead-time.md)) and shown on the dashboard once the slider passes the flag.
- Evacuation routes: `get_evacuation_route` and `get_rescue_route` are real. Residents go to the nearest safe point the forecast does not reach, avoiding the area burned by the scenario time plus the next hour of predicted spread; crews avoid only what has burned ([why](docs/findings/2026-09-19-evacuation-destinations.md)). Click a resident on the map to see their route by car or on foot, and the directions the agent reads them. Demo routes are cached in `data/`.
- Evacuation orders per zone: the system proposes a destination (or staying indoors) for each zone with residents, the coordinator approves or changes it, and the agent reads that order to everyone in the zone, then gives each resident their own route to it.
- Demo mode: a typed answer (classified by the LLM) or three buttons replace a failed call, map tiles are cached for a flaky network, and Reset restores everything between rehearsals. See [docs/demo/runbook.md](docs/demo/runbook.md).
- Voice agents (Unmute packages in `voice/`): the resident agent is deployed on SLNG (Spanish, Nemotron Super 3, Castilian voice) and changes a pin from SLNG's browser test; the coordinator agent, which reads the rescue queue and the crew's route while the dashboard draws it, is packaged but not deployed yet.
- Crew alerts: every new *needs rescue* creates an alert with the address, people, mobility and a link that opens the dashboard on the crew's route from the El Tiemblo fire station. Shown on the dashboard, and texted to the crew by SMS once Twilio credentials are set.

Still to build: outbound phone calls, which need a phone number (#8), and deploying the coordinator agent (#10). See [PLAN.md](PLAN.md) and the issues.

## Architecture

A single repo, run on localhost and deployed straight from `main` as one Railway service: the backend serves the API, the agent tools and the built dashboard on one URL ([Deployment](docs/setup/deployment.md)). No staging environment.

```
frontend/src/
  domain/      Types and pure functions. No React, no fetch, no styling
  services/    Backend client: the only place that knows URLs and HTTP
  hooks/       State and polling; returns plain data
  ui/          Presentational components, theme and CSS. Props in, markup out
backend/app/
  main.py      Dashboard API (/api) and agent tools (/tools)
  models.py    The tool contract
  state.py     Triage state, rescue prioritisation and the replay clock
  spread.py    Predicted spread: a cone from the front's velocity
  impact.py    Which zones the predicted spread reaches, and when
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
