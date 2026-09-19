# Setting up a new machine

From a fresh laptop to the dashboard running on localhost. About 10 minutes. Tested on Ubuntu under WSL2; macOS and native Linux work the same way. On Windows, use WSL2 and clone inside the Linux filesystem (`~/`), not under `/mnt/c`, which is much slower.

## 1. Tools

| Tool | Why | Install | Check |
|---|---|---|---|
| Git | Clone and push | Your OS package manager | `git --version` |
| GitHub CLI | Issues, pull requests | https://cli.github.com, then `gh auth login` | `gh auth status` |
| Node 20+ | Frontend toolchain | https://nodejs.org or `nvm install --lts` | `node --version` |
| pnpm 10 | Frontend packages and repo scripts | `corepack enable` (Node ships Corepack; it picks the version pinned in `package.json`) | `pnpm --version` |
| uv | Python and backend packages | `curl -LsSf https://astral.sh/uv/install.sh \| sh`, then open a new shell | `uv --version` |
| Claude Code | Optional, AI-assisted development | https://docs.claude.com/en/docs/claude-code | `claude --version` |

You do not need to install Python yourself: `uv` downloads Python 3.12 if the machine lacks it.

pnpm only. No `npm install`, no `yarn`, no `npx` (use `pnpm dlx`).

## 2. Clone and install

```bash
git clone https://github.com/RogerTito455/hackfire.git
cd hackfire
pnpm bootstrap          # pnpm install + uv sync
```

Do **not** run `pnpm setup`: that is a pnpm built-in that edits your shell profile, and it shadows any script with the same name. See [the finding](../findings/2026-09-19-local-setup.md).

## 3. Keys

```bash
cp .env.example .env
```

Fill in the keys you have; the team shares them through a private channel, never through git. [Environment variables](environment.md) lists what each one unlocks. The skeleton runs with none of them.

Keep `.env` to `KEY=value` lines and `#` comments. Pasted notes or curl snippets break the parser, and the variables after them silently go missing.

## 4. Run

Two terminals:

```bash
pnpm dev:api            # backend  — http://localhost:8000, API docs at /docs
pnpm dev:web            # frontend — http://localhost:5173
```

Smoke test the triage flow without the voice agent:

```bash
curl -X POST localhost:8000/tools/report_status \
  -H 'Content-Type: application/json' \
  -d '{"neighbor_id":"n02","status":"needs_rescue","people":2,"mobility":"cannot walk"}'
```

The pin for `n02` turns red within two seconds and the resident appears in the rescue queue. `curl -X POST localhost:8000/api/reset` restores the demo.

## 5. Check before every commit

```bash
pnpm check              # backend tests, then frontend type-check and build
```

## 6. Optional

- **Claude Code with the project's MCP servers and skills:** [claude-code.md](claude-code.md).
- **Demo registry with real phones:** `data/neighbors.local.json` (git-ignored) is picked up automatically when it exists; `HACKFIRE_NEIGHBORS_FILE` points elsewhere. It holds 10 residents on real streets of La Atalaya and El Tiemblo with `REPLACE-ME-NN` where a phone goes: ask a teammate for the team's copy, or fill in your own. Never commit it. Tests ignore it and use the sample registry. On Railway it is a variable, see [Deployment](deployment.md#the-real-registry).
- **Cached fire data:** `pnpm data:hotspots` needs the Deepfire keys. See [Deepfire](../services/deepfire.md). The committed files in `data/` are enough to run the demo: `pnpm data:zones` (no key, see [Overpass](../services/overpass.md)) and `pnpm data:spread` (no network) only regenerate them.

## Troubleshooting

| Symptom | Cause and fix |
|---|---|
| `ERR_PNPM_BAD_SHELL_SECTION` or pnpm edits `~/.bashrc` | You ran `pnpm setup`. Use `pnpm bootstrap` |
| `Failed to resolve import "…"` in the browser, or `ModuleNotFoundError` in the backend, right after `git pull` | Someone added a dependency. Run `pnpm bootstrap`, then restart `pnpm dev:web` / `pnpm dev:api` |
| `uv: command not found` right after installing | Open a new shell, or `export PATH="$HOME/.local/bin:$PATH"` |
| `python-dotenv could not parse statement starting at line N` | Line N of `.env` is not `KEY=value`. Prefix it with `#` or move it out |
| A key is set in `.env` but the backend sees it empty | Check the name against `.env.example`; the backend reads exactly those names |
| Dashboard loads but shows no residents | The backend is not running, or `VITE_API_URL` in `frontend/.env.local` points elsewhere |
