# Claude Code: MCP servers and skills

The team uses Claude Code to build HackFire. The repo ships shared configuration so every teammate gets the same tools after `git pull`:

- `.mcp.json`: MCP servers for the project, all without secrets
- `.claude/skills/`: project skills, pinned in `skills-lock.json`
- `CLAUDE.md`: the rules Claude follows in this repo

These are **development tools**. They help us write the code; the app itself calls each service through `backend/app/providers/`.

## MCP servers

### Shared, in `.mcp.json`

The first time you run `claude` in the repo it asks you to approve these. `/mcp` shows their status and runs the OAuth sign-in where one is needed.

| Server | URL | Auth | What it gives Claude |
|---|---|---|---|
| `deepfire` | `https://api.deepfire.co/mcp` | None | Search reported fires worldwide (`deepfire_search_fires`, `deepfire_get_fire`). Not raw hotspots, not spread runs |
| `slng-docs` | `https://docs.slng.ai/mcp` | None | Search the SLNG docs. Undocumented endpoint, found working on 2026-09-19 |
| `deepwiki` | `https://mcp.deepwiki.com/mcp` | None | Ask questions about any public GitHub repo (MapLibre, openrouteservice, FastAPI) |
| `norma` | `https://api.qualityclouds.ai/mcp` | OAuth (browser, first use) | Extension 1: code-quality rules and findings. See [Norma](../services/norma.md) |

They were added with commands, not by editing the file:

```bash
claude mcp add --scope project --transport http deepfire https://api.deepfire.co/mcp
claude mcp add --scope project --transport http slng-docs https://docs.slng.ai/mcp
claude mcp add --scope project --transport http deepwiki https://mcp.deepwiki.com/mcp
claude mcp add --scope project --transport http norma https://api.qualityclouds.ai/mcp
```

### Personal, per teammate

These need your own credentials, so each person adds them to their own user scope. They never go in `.mcp.json`.

| Server | When | Command |
|---|---|---|
| Supabase | Only if the team adopts it; see [Supabase](../services/supabase.md) | Install the Supabase plugin, or `claude mcp add --scope user --transport http supabase "https://mcp.supabase.com/mcp?project_ref=<id>&read_only=true"` |
| Devin | Extension 3, once Cognition gives us access | `claude mcp add --scope user --transport http devin https://mcp.devin.ai/mcp -H "Authorization: Bearer <cog_ key>"` |

## Skills

Project skills live in `.claude/skills/` and load automatically. Claude picks one when the task matches its description; you can also ask for it by name.

| Skill | Source | Use it for |
|---|---|---|
| `tdd` | [mattpocock/skills](https://github.com/mattpocock/skills) | Building a slice test-first: one test, one implementation, repeat. Fits the `/tools` contract and pytest |
| `diagnosing-bugs` | [mattpocock/skills](https://github.com/mattpocock/skills) | Hard bugs: build a failing curl or test first, then fix. Redacts secrets in what it shows |
| `maplibre-v6-migration` | [maplibre/maplibre-agent-skills](https://github.com/maplibre/maplibre-agent-skills) | MapLibre v6 specifics: no default export, ESM only, `setWorkerUrl()` under Vite |
| `maplibre-source-wiring` | [maplibre/maplibre-agent-skills](https://github.com/maplibre/maplibre-agent-skills) | A layer that does not render, `source-layer` mismatches, `setFeatureState` doing nothing |
| `agent-prompt` | [slng-ai/skills](https://github.com/slng-ai/skills) | Drafting the greeting, system prompt, variables and tools for the SLNG Agent Builder (#7) |
| `agents` | [slng-ai/skills](https://github.com/slng-ai/skills) | Creating SLNG agents and dispatching calls through the API (#8, #10). Reads `VOICEAI_API_KEY` |
| `unmute`, `unmute-deploy`, `unmute-manifest` | The `unmute` CLI, v0.5.5 | Writing and validating the voice agents in `voice/` (`unmute`), pushing them to SLNG (`unmute-deploy`). `unmute-manifest` is for organisation contracts, which we do not use |

Built into Claude Code and worth using: `/code-review` on a branch before merging, and `/simplify` after a slice lands.

### Managing skills

The installer is the `skills` CLI. Use `pnpm dlx`, never `npx`.

```bash
pnpm dlx skills@latest add <owner/repo> -s <skill> [<skill>…] -a claude-code -y   # add
pnpm dlx skills@latest add <owner/repo> -l                                        # list without installing
pnpm dlx skills@latest update -p -y                                               # update project skills
pnpm dlx skills@latest remove -s <skill> -y                                       # remove
```

Commit `.claude/skills/` and `skills-lock.json` together. Skills run with Claude's full permissions: read a skill's `SKILL.md` before adding it.

The Unmute skills are the exception: they ship inside the `unmute` binary, not through the `skills` CLI, so they are not in `skills-lock.json`. The text lives in `.agents/skills/unmute*/` and `.claude/skills/unmute*/SKILL.md` only points there. After updating the CLI, refresh them from the repo root with `unmute skill install` (it refuses to overwrite local edits without `--force`), and commit both folders.

### Installed later, only when needed

- **`norma-workflow`** (from [qualityclouds/norma-mcp](https://github.com/qualityclouds/norma-mcp)): makes Claude run Norma's checks on *every* file it touches while the `norma` server is connected. Right for extension 1 at 22:00; it would slow the core build before then. See [Norma](../services/norma.md).

### What we chose not to install, and why

- **The rest of mattpocock/skills.** The planning skills (`to-spec`, `to-tickets`, `triage`, `grill-me`) duplicate PLAN.md and the slice issues. `setup-matt-pocock-skills` rewrites CLAUDE.md. `git-guardrails` blocks `git push`. `resolving-merge-conflicts` commits on its own. The architecture skills work on a longer horizon than a hackathon.
- **anthropics/skills.** `web-artifacts-builder` relies on shadcn and Tailwind, which the no-component-kit rule forbids. The `pptx` skill could help with the pitch deck (#15) if we build one: `/plugin install document-skills@anthropic-agent-skills`.
- **The rest of slng-ai/skills.** `setup-api-key`, `text-to-speech` and `speech-to-text` overlap with what the docs MCP and the curl in [SLNG](../services/slng.md) already give; the three migration skills are for moving an existing LiveKit or Pipecat agent.
- **supabase/agent-skills.** Identical to what the Supabase plugin already provides, and Supabase is not adopted.
- **fastapi/fastapi skill.** It pushes `fastapi dev` and a hand-written `pyproject.toml` section, both against our conventions.
