# Supabase

**Used for:** nothing yet. Supabase is **not in PLAN.md**; adopting it is a team decision.
**Status:** not adopted. A project exists and some teammates have its keys, but no code reads them

## Where it could fit

PLAN.md keeps triage state in memory in one long-running backend process (#2). Supabase would earn its place only if one of these becomes a real problem:

| Need | What Supabase would give |
|---|---|
| State must survive a backend restart or redeploy during the demo | Triage state in Postgres |
| The backend has to run serverless (#2 rules this out while state is in memory) | A hosted store shared across invocations |
| Polling every 2 s is too slow or too heavy | Realtime: the dashboard subscribes to status changes |

Each of these costs time on Saturday afternoon, and none is required for the four steps. If the team adopts it, record the decision in PLAN.md first, then follow the rules below.

## If adopted

- **Backend** (the only place that writes): `SUPABASE_URL` and `SUPABASE_SECRET_KEY` (`sb_secret_…`) in `.env`, read in `config.py`, used from a module in `backend/app/providers/`. The secret key bypasses row-level security; it never leaves the backend.
- **Frontend** (read-only, Realtime): `VITE_SUPABASE_URL` and `VITE_SUPABASE_PUBLISHABLE_KEY` (`sb_publishable_…`) in `frontend/.env.local`, used only from `frontend/src/services/`. Enable row-level security on every table the browser can see.
- **Never expose `Neighbor.phone`.** Phone numbers stay out of any table the publishable key can read.
- The `NEXT_PUBLIC_*` names in Supabase's snippets are for Next.js. This is a Vite app, so the prefix is `VITE_`.
- Legacy `anon` and `service_role` keys are being deprecated by the end of 2026; use the new keys.
- Add each variable to `.env.example` (empty) and to [environment.md](../setup/environment.md) in the same commit.

## In Claude Code

Per teammate, in user scope (it uses OAuth, so there is no secret to share):

```bash
claude mcp add --scope user --transport http supabase \
  "https://mcp.supabase.com/mcp?project_ref=<project id>&read_only=true"
```

`project_ref` limits the server to our project, and `read_only=true` stops Claude from changing the database. The Supabase Claude Code plugin gives the same server plus the `supabase` and `supabase-postgres-best-practices` skills.

## Sources

- MCP: https://supabase.com/docs/guides/getting-started/mcp
- API keys: https://supabase.com/docs/guides/api/api-keys
- React quickstart: https://supabase.com/docs/guides/getting-started/quickstarts/reactjs
