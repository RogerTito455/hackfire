# Norma (QualityClouds)

**Used for:** extension 1 (#17): one scan, at least one fix, one rescan, and the before/after delta for the "defend your code" talk. Covers "validate for production".
**Status:** done (#17). Scanned on 2026-09-20 with `live_check`, three findings fixed, the delta and the
reasoning in [docs/findings/2026-09-20-norma-scan.md](../findings/2026-09-20-norma-scan.md)
**Owner:** Bryan

## Access

No key in `.env`. Norma is an MCP server with OAuth: the first time Claude uses it, a browser window asks you to sign in. There is a permanent free tier. Findings are also visible at https://norma.qualityclouds.com.

## In Claude Code

The `norma` server is in `.mcp.json` (`https://api.qualityclouds.ai/mcp`). Run `/mcp` to approve it and sign in.

It covers Python, FastAPI, TypeScript, React and Vite, so both halves of the repo, across six areas: security, performance, scalability, manageability, maintainability and architecture.

| Tool | What it does |
|---|---|
| `link_repository` | Links this repo. Refuses this one: `auto_import_not_available` (see below) |
| `get_rulesets`, `get_rules_for_ruleset` | Which rules apply |
| `live_check` | Checks one file |
| `get_open_issues` | Results of the last full scan. Needs the repo imported in the portal; unavailable here |
| `register_applied_actions` | Records the fixes we made, for the delta |

## The 45-minute run

0. Install the vendor's workflow skill, which walks Claude through the loop below and records results with the exact rule ids:

   ```bash
   pnpm dlx skills@latest add qualityclouds/norma-mcp -s norma-workflow -a claude-code -y
   ```

   Not before 22:00: while it is installed and the server is connected, Claude runs Norma on every file it edits.

1. `link_repository`, then `get_open_issues`: save the list as the "before".
2. Pick one or two findings worth defending (security first), fix them, run `pnpm check`.
3. `register_applied_actions`, then rescan and save the "after".
4. Write the delta and the reasoning in a finding: `docs/findings/YYYY-MM-DD-norma-scan.md`.

**Answered (2026-09-20):** a full repository scan needs the repository imported in the Norma portal first. There is
no way to trigger the import from the MCP server for a private repo: `link_repository` returns
`{"outcome": "failed", "reason": "auto_import_not_available"}`, and until that is done `get_open_issues` and
`register_applied_actions` both refuse with `unlinked`. `live_check` works without a link and is deterministic, so
the pass was run file by file with it. Import the repository in the portal to unlock the full scan and the
compliance audit trail.

## Sources

- https://github.com/qualityclouds/norma-mcp (README, `mcp.json`, `skills/norma-workflow/SKILL.md`)
