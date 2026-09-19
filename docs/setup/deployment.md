# Deployment

**Status:** working at https://frontend-production-ae2c.up.railway.app since 2026-09-19. Checked from outside: `/health`, the dashboard and its assets, `report_status` → rescue queue → `POST /api/reset`, and a push to `main` redeploying (the served bundle matched a fresh build of `main`).
**Issue:** #2

HackFire deploys as **one Railway service**: the FastAPI backend serves the API, the agent tools and the built dashboard, all on one HTTPS URL. Pushing to `main` redeploys it.

## Why one service on Railway

| Option | Verdict |
|---|---|
| **Cloudflare Workers** | No. Triage state lives in the process's memory, and Workers run in [isolates](https://developers.cloudflare.com/workers/reference/how-workers-works/) with no guarantee that two requests reach the same one, so a `report_status` can land in one isolate and the dashboard poll in another (the note in #2 says the same). Moving the state to [Durable Objects](https://developers.cloudflare.com/durable-objects/) and the backend onto [Python Workers](https://developers.cloudflare.com/workers/languages/python/) is a rewrite that does not fit the hackathon. |
| **Vercel (frontend) + Railway (backend)** | Works, but it is two platforms, two dashboards, a CORS origin and a `VITE_API_URL` to keep in sync. The team wanted everything in one place. |
| **Render, free plan** | Spins the service down after 15 minutes without traffic, which wipes the triage state and takes about a minute to wake. Too risky on stage. |
| **Railway, one service** | Chosen. A long-running container that does not sleep, HTTPS out of the box for the SLNG tools, and it builds the root `Dockerfile` with no configuration. |

With the dashboard on the same origin as the API, the deployed site needs no CORS and no `VITE_API_URL`.

## How the image is built

The root [`Dockerfile`](../../Dockerfile) has two stages:

1. **Dashboard:** Node 24, `corepack enable` (pnpm at the version pinned in `package.json`), `pnpm install --frozen-lockfile`, `pnpm build`.
2. **API:** uv on Python 3.12, `uv sync --locked --no-dev`, then `backend/app`, `data/` and the built `frontend/dist`. The Dockerfile sets `HACKFIRE_DASHBOARD_DIR`, which makes the backend serve `/`, `/favicon.svg` and `/assets/*` from the build (`backend/app/main.py`). Every other path is the API, unchanged. Locally the variable is empty and Vite serves the dashboard as before.

It starts `uvicorn` with a single worker on `$PORT`. The Dockerfile lives at the repo root because the build needs `frontend/`, `backend/` and `data/`, and because Railway only auto-detects a Dockerfile at the root.

[`.dockerignore`](../../.dockerignore) keeps `.env` files at any depth (including `frontend/.env.local`, which would bake a `VITE_API_URL` into the bundle), `data/neighbors.local.json` and `NOTES.internal.md` out of the image, even when it is built on a laptop.

## Setting up the Railway service (once)

Done on 2026-09-19. Railway's import reads the pnpm workspace and configures the service as if it were the `frontend` package, so several settings have to be corrected by hand. See [the finding](../findings/2026-09-19-railway-pnpm-workspace-import.md).

1. Sign in at https://railway.com with GitHub.
2. **New Project → Deploy from GitHub repo → `RogerTito455/hackfire`**. Grant the Railway GitHub app access to the repo if asked. Railway names the service `frontend` and builds the root `Dockerfile`.
3. Correct what the import set, in the service settings:

   | Setting | Set by the import | Set it to |
   |---|---|---|
   | Start command | `pnpm --filter frontend dev` | `/bin/sh -c "exec uvicorn app.main:app --host 0.0.0.0 --port $PORT"` (the Dockerfile's `CMD`; clearing the field was not enough) |
   | Build command | `pnpm --filter frontend build` | Empty; the Dockerfile builder ignores it |
   | Watch patterns | `/frontend/**` | Empty, so every push deploys. With only `/frontend/**`, Railway silently skipped every backend-only commit (they show under **Show Skipped** in Deployments), and a backend fix sat undeployed while we debugged the old code |
   | Region | `sfo` (US West) | EU West (Amsterdam), next to the demo and to the voice agent |
   | Healthcheck path | none | `/health` |
   | Replicas | 1 | Keep 1: a second replica would hold a second, different triage state |

   Apply the staged changes; editing a field does not redeploy by itself.
4. **Networking → Generate Domain.** Railway does not detect the port; enter `8080`, the `PORT` it injects (the deploy log prints `Uvicorn running on http://0.0.0.0:8080`).
5. Check that the source branch is `main` with automatic deploys on.
6. **Variables:** none are needed for the skeleton. Add keys as the slices that read them land (`DEEPFIRE_CLIENT_ID` and `DEEPFIRE_CLIENT_SECRET` for live mode, then Nebius, ORS and SLNG). Never set `HACKFIRE_NEIGHBORS_FILE` to a laptop path. See [Environment variables](environment.md).

Railway's config-as-code file (`railway.toml`) is not an option for this service: new services cannot use it. See [the finding](../findings/2026-09-19-railway-config-as-code-deprecated.md).

## The real registry

The registry with the team's own phone numbers (#12) reaches the deployed backend as a Railway variable, so it is neither in git nor in the image.

1. Put the team's real numbers in `data/neighbors.local.json` on your machine (it is git-ignored and starts with `REPLACE-ME-NN` placeholders).
2. Print it as one line and copy it: `python3 -c "import json;print(json.dumps(json.load(open('data/neighbors.local.json')),ensure_ascii=False,separators=(',',':')))" | pbcopy`
3. In Railway, **Variables → New Variable → `HACKFIRE_NEIGHBORS_JSON`**, paste, and deploy. The variable wins over every file.
4. Check from outside: `curl -s $B/api/neighbors` lists the residents and no phone number anywhere in the response (`Neighbor.phone` is never serialised).

A malformed value stops the backend at start-up with a message that names the variable and the field, never the content, so the deploy log does not leak a number. Changing the variable redeploys the service and wipes the triage state.

The routes are cached by coordinates (`data/routes_cache.json`, see [openrouteservice](../services/openrouteservice.md)): a resident that is not in the cache costs a live openrouteservice call, and without `ORS_API_KEY` on Railway that route answers 503. After changing the registry, run `pnpm data:routes` with a key that still has quota and commit the file; it holds coordinates and directions, never names or phones. Today only n01 to n05 are cached: n06 to n10 answer 503 until it is rerun.

## Checking a deploy

```bash
B=https://<service>.up.railway.app
curl -s $B/health                                    # {"status":"ok"}
curl -s -X POST $B/tools/report_status \
  -H 'Content-Type: application/json' \
  -d '{"neighbor_id":"n02","status":"needs_rescue","people":2,"mobility":"cannot walk"}'
curl -s -X POST $B/api/reset                         # back to the initial registry
```

With `$B` open in a browser, the `n02` pin turns red at the next poll: within about two seconds, since the dashboard polls every 2 s and then waits for the round trip.

## Gotchas

- **A 502 "Application failed to respond" means the process died**; a Python error would be a 500. To tell, mark a resident with `report_status`, repeat the failing request, and check whether the mark survived: the state is in memory, so a restart wipes it. On 2026-09-19 the first `/api/fire-area` call buffered ~3,000 hotspots in one GEOS pass, peaked at ~1.9 GB and got killed; `replay.burned_area_m` now takes 0.2 s and 54 MB. The image sets `PYTHONFAULTHANDLER=1`, so a crash in native code (GEOS, numpy) prints where it happened to the deploy logs.
- **Check which commit is Active** before debugging a deploy. The Deployments tab names it; a push that did not match the watch patterns never shows up there.
- **Every deploy wipes the triage state.** The state is in memory, so a restart reloads the registry. Nobody pushes to `main` during the demo. If state has to survive a redeploy, see [Supabase](../services/supabase.md).
- **The real registry is not in the image.** `data/neighbors.local.json` is git-ignored, so without the variable below the deployed backend serves `neighbors.sample.json`. See [The real registry](#the-real-registry).
- **A frontend-only change also restarts the backend**, because they are one service.
- **CORS only matters for a dashboard on another origin**, such as `pnpm dev:web` pointed at the deployed backend with `VITE_API_URL`. Add that origin to `HACKFIRE_CORS_ORIGINS` on Railway.

## Building the image locally

```bash
docker build -t hackfire:local .
docker run --rm -e PORT=8080 -p 8080:8080 hackfire:local    # http://localhost:8080
```

On WSL2 with Docker Engine rather than Docker Desktop, two things got in the way:

- `error getting credentials - err: exec: "docker-credential-desktop.exe"`: `~/.docker/config.json` names Docker Desktop's credential helper. Build with an empty config: `DOCKER_CONFIG=$(mktemp -d) docker build …`.
- `EAI_AGAIN registry.npmjs.org` during `pnpm install`: DNS does not resolve inside the build container. Add `--network host` to `docker build`.

There is no `bookworm` tag for uv 0.11, so the Dockerfile uses `ghcr.io/astral-sh/uv:0.11-python3.12-trixie-slim`.

## Sources

- Railway, Dockerfiles: https://docs.railway.com/builds/dockerfiles
- Railway, `PORT` and healthchecks: https://docs.railway.com/deployments/healthchecks
- Railway, binding to `0.0.0.0:$PORT`: https://docs.railway.com/reference/errors/application-failed-to-respond
- Railway, config as code deprecated: https://docs.railway.com/infrastructure-as-code
- Render free plan spin-down: https://render.com/docs/free
