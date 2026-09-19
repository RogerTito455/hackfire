# Railway configures a pnpm workspace as its frontend package

**Date:** 2026-09-19 · **Area:** Deployment

## What happened

Importing the repo into Railway created a service named `frontend`, after the only package in `pnpm-workspace.yaml`. It built the root `Dockerfile` as expected, then failed at **Deploy › Create container** with:

```
The executable `pnpm` could not be found.
```

The service configuration showed what the import had set on its own:

- Start command `pnpm --filter frontend dev`
- Build command `pnpm --filter frontend build`
- Watch patterns `/frontend/**`
- Region `sfo`

## Why

The custom start command overrides the Dockerfile's `CMD`. The final image is the Python stage, which has no pnpm; pnpm only exists in the stage that builds the dashboard. Even with pnpm present, the command would have started Vite's dev server instead of the API.

## What we do about it

For #2:

- Set the start command explicitly to the Dockerfile's `CMD`: `/bin/sh -c "exec uvicorn app.main:app --host 0.0.0.0 --port $PORT"`. Clearing the field was not enough.
- Empty the build command, widen the watch patterns, and move the region to EU West. [Deployment](../setup/deployment.md) has the full table.
- Generating the domain asked for the port by hand: `8080`.

## Sources

- https://docs.railway.com/builds/dockerfiles
- https://docs.railway.com/guides/monorepo
