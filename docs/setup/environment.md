# Environment variables

The backend reads every variable in one place, `backend/app/config.py`, which loads the repo-root `.env` on start-up. Variables already set in the process (tests, the hosting platform) take precedence over `.env`. The frontend reads only `VITE_*` variables, from `frontend/.env.local`.

`.env.example` must list every variable the code reads, with an empty value. Adding a variable means adding it to `config.py`, `.env.example` and this page, in the same commit.

## Backend (`.env`)

| Variable | Needed for | Where to get it |
|---|---|---|
| `HACKFIRE_CORS_ORIGINS` | A dashboard on another origin calling this backend, such as `pnpm dev:web` against the deployed one. The deployed dashboard is same-origin and needs nothing | Comma-separated origins; spaces and trailing slashes are ignored. Default `http://localhost:5173` |
| `HACKFIRE_DASHBOARD_DIR` | The deployed backend serving the built dashboard | Set in the `Dockerfile` to `/repo/frontend/dist`. Leave empty locally, where `pnpm dev:web` serves it. See [Deployment](deployment.md) |
| `HACKFIRE_NEIGHBORS_FILE` | Demo with the real registry (#12) | Path to `data/neighbors.local.json`. Empty uses `data/neighbors.local.json` if it exists, else the sample registry |
| `HACKFIRE_NEIGHBORS_JSON` | The real registry on Railway (#12), where the local file is not in the image | The whole registry as one line of JSON, set as a Railway variable. Wins over every file. See [Deployment](deployment.md#the-real-registry). Holds phone numbers: never commit it or paste it in a chat |
| `HACKFIRE_CREWS` | The crews' plan (`GET /api/crew-plan`, the coordinator agent's `get_crew_plan`) | How many fire crews share the rescues. Default 2; the dashboard can change it |
| `HACKFIRE_CREW_PHONE` | Crew notification for each new rescue (#9) | A team member's phone, shared privately |
| `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_FROM_NUMBER` | The crew SMS (#9). All three plus `HACKFIRE_CREW_PHONE`, or alerts stay on the dashboard | Twilio console → Account info; the from number must be SMS-capable. Ask the SLNG mentors if they lend one |
| `HACKFIRE_PUBLIC_URL` | The link in each crew alert (#9) | The deployed dashboard URL. Empty means `http://localhost:5173` |
| `HACKFIRE_SCENARIO` | Which fire the backend replays, and every pipeline (`pnpm data:*`, `check:routes`) reads and writes: its box, dates, lead-time zone and data files | An id of `data/scenarios/<id>.json`, or a path to a scenario file relative to the repo root. Empty means `el-tiemblo-2026-07-23`, the demo. See [A new scenario](new-scenario.md) |
| `HACKFIRE_SCENARIO_TIME` | The replay moment the calls happen at: routes avoid the fire burned up to then, and `get_fire_status` answers for it until the dashboard's slider sets another (#4) | ISO 8601. Empty means the scenario's `scenario_time`; the demo's is `2026-07-23T16:00:00Z` (18:00 CEST): after La Atalaya is first flagged (15:30 CEST), with about 4 h to impact and safe ways out still open. After changing it, run `pnpm data:routes` |
| `HACKFIRE_AGENT_LOCALE` | The language of what the voice agents are told: tool answers (`get_fire_status`, routes, orders) and each call's data. Any code in `backend/app/locales/` | Empty means `en`. `es` makes the agents receive Spanish sentences; try it with `pnpm eval:triage` before a demo |
| `HACKFIRE_CREW_LOCALE` | The language of the texts to the crews: the crew alert SMS and the crews' map-room link (the dashboard shows each alert in its own language) | Empty means `es` |
| `HACKFIRE_RESIDENT_LOCALE` | The language of the texts to residents, such as the video link SMS (#18). The voice agent's spoken language is set in its prompt | Empty means `es` |
| `DEEPFIRE_CLIENT_ID` | Hotspots, live fires, spread (#3, #4, #11) | https://app.deepfire.co → Settings → API clients → Create |
| `DEEPFIRE_CLIENT_SECRET` | Same | Shown once when the API client is created |
| `SLNG_API_KEY` | Voice agent, calls, SMS (#7, #8, #9, #10) | https://app.slng.ai → Projects → Generate key |
| `SLNG_BASE_URL` | Same | See [SLNG](../services/slng.md) |
| `SLNG_RESIDENT_AGENT_ID` | The call campaign and the dashboard's *Call … (answer here)* (#8) | The resident agent's id; defaults to `hackfire-resident-slng` (`0f035ccc-…`). `voiceai agents list` shows it |
| `SLNG_COORDINATOR_AGENT_ID` | The dashboard's *Ask the coordinator agent* (#10) | The coordinator agent's id; defaults to `hackfire-coordinator-slng` (`6d1a743a-…`) |
| `VONAGE_APPLICATION_ID` | Live video from a resident who needs rescue, with captions (#18) | https://developer.vonage.com → Applications → Create a new application → Generate public and private key → Video capability on |
| `VONAGE_PRIVATE_KEY` | Same | The PEM text of the key downloaded then (one line with `\n` works, as on Railway), or a path to the `.key` file. Never commit it |
| `VONAGE_SMS_FROM` | Texting the video link to the resident (#18) | Sender name, up to 11 letters or digits; default `HackFire`. A trial account only texts numbers on its test list |
| `HACKFIRE_PHONE_CALLS` | Phoning residents from the call campaign (#8) | `1` once an outbound SIP trunk is attached to the agent in SLNG; anything else keeps phones off and the dashboard offers browser calls |
| `SLNG_LLM_URL` | The backend's LLM: typed answers on the dashboard and `pnpm eval:triage`, with `SLNG_API_KEY` | SLNG's Context Router. Default `https://eu-north.context-router.slng.ai/v1` |
| `SLNG_LLM_MODEL` | Same | Default `bedrock-mantle/nvidia.nemotron-super-3-120b:latest`, the model the voice agents think with |
| `GALTEA_API_KEY` | `pnpm eval:galtea` only: simulated residents against the resident agent, with `SLNG_API_KEY`. The app never reads it | https://platform.galtea.ai → Settings. See [Galtea](../services/galtea.md) |
| `ORS_API_KEY` | Evacuation and rescue routes (#6); only needed to plan routes that are not in `data/routes_cache.json` | https://openrouteservice.org/dev/#/signup |
| `OVERPASS_URL` | `pnpm data:zones` (#4); optional, no key | Empty uses `https://overpass-api.de/api/interpreter`. See [Overpass](../services/overpass.md) if it refuses connections |

## Frontend (`frontend/.env.local`)

| Variable | Needed for | Value |
|---|---|---|
| `VITE_API_URL` | Pointing a local dashboard at another backend, such as the deployed one | Backend URL. Defaults to `http://localhost:8000` under `pnpm dev:web`, and to the page's own origin in a production build, so `vite preview` needs it set |

Vite exposes `VITE_*` variables to the browser bundle, so anything placed there is public. Never put a secret key in a `VITE_*` variable.

## Deployed (Railway)

Railway injects `PORT`, which the `Dockerfile` passes to uvicorn; nothing else reads it. Every other backend variable is set in the Railway service's variables, never in the image. See [Deployment](deployment.md).

## Not read by the code

Some people have extra keys in their `.env` (for example Supabase, from exploring it). Nothing in the repo reads them until the team adopts the service; see [Supabase](../services/supabase.md). Keys for the extensions (Norma, Devin, Vonage) are configured in Claude Code or the vendor's dashboard, not in `.env`, unless the code starts calling them.

## Rules

- `.env` is git-ignored; `.env.example` is tracked and holds names only.
- Share keys through a private channel, never in an issue, commit, pull request or screenshot.
- Before the repo goes public (#16), `git log -p | grep -i -E "api_key|secret|token"` must find nothing real.
