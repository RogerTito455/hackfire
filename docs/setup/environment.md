# Environment variables

The backend reads every variable in one place, `backend/app/config.py`, which loads the repo-root `.env` on start-up. Variables already set in the process (tests, the hosting platform) take precedence over `.env`. The frontend reads only `VITE_*` variables, from `frontend/.env.local`.

`.env.example` must list every variable the code reads, with an empty value. Adding a variable means adding it to `config.py`, `.env.example` and this page, in the same commit.

## Backend (`.env`)

| Variable | Needed for | Where to get it |
|---|---|---|
| `HACKFIRE_CORS_ORIGINS` | A dashboard on another origin calling this backend, such as `pnpm dev:web` against the deployed one. The deployed dashboard is same-origin and needs nothing | Comma-separated origins; spaces and trailing slashes are ignored. Default `http://localhost:5173` |
| `HACKFIRE_DASHBOARD_DIR` | The deployed backend serving the built dashboard | Set in the `Dockerfile` to `/repo/frontend/dist`. Leave empty locally, where `pnpm dev:web` serves it. See [Deployment](deployment.md) |
| `HACKFIRE_NEIGHBORS_FILE` | Demo with the real registry (#12) | Path to `data/neighbors.local.json`. Empty uses the sample registry |
| `HACKFIRE_CREW_PHONE` | Crew notification for each new rescue (#9) | A team member's phone, shared privately |
| `HACKFIRE_SCENARIO_TIME` | The replay moment the calls happen at: routes avoid the fire burned up to then | ISO 8601. Empty means `2026-07-23T18:30:00Z` (20:30 CEST), when the front was ~4 km from La Atalaya. After changing it, run `pnpm data:routes` |
| `DEEPFIRE_CLIENT_ID` | Hotspots, live fires, spread (#3, #4, #11) | https://app.deepfire.co → Settings → API clients → Create |
| `DEEPFIRE_CLIENT_SECRET` | Same | Shown once when the API client is created |
| `SLNG_API_KEY` | Voice agent, calls, SMS (#7, #8, #9, #10) | https://app.slng.ai → Projects → Generate key |
| `SLNG_BASE_URL` | Same | See [SLNG](../services/slng.md) |
| `NEBIUS_API_KEY` | LLM for the agent and the triage (#7) | https://tokenfactory.nebius.com |
| `NEBIUS_BASE_URL` | Same | `https://api.tokenfactory.nebius.com/v1` |
| `NEBIUS_MODEL` | Same | A model id from the catalogue; see [Nebius](../services/nebius.md) |
| `ORS_API_KEY` | Evacuation and rescue routes (#6); only needed to plan routes that are not in `data/routes_cache.json` | https://openrouteservice.org/dev/#/signup |

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
