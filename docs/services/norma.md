# Norma (QualityClouds)

**Used for:** extension 1 (#17): one scan, at least one fix, one rescan, and the before/after delta for the "defend your code" talk. Covers "validate for production".
**Status:** extension, not started. Planned for Saturday 22:00, only if the core works end to end
**Owner:** Bryan

## Access

No key in `.env`. Norma is an MCP server with OAuth: the first time Claude uses it, a browser window asks you to sign in. There is a permanent free tier. Findings are also visible at https://norma.qualityclouds.com.

## In Claude Code

The `norma` server is in `.mcp.json` (`https://api.qualityclouds.ai/mcp`). Run `/mcp` to approve it and sign in.

It covers Python, FastAPI, TypeScript, React and Vite, so both halves of the repo, across six areas: security, performance, scalability, manageability, maintainability and architecture.

| Tool | What it does |
|---|---|
| `link_repository` | Links this repo. Call it first |
| `get_rulesets`, `get_rules_for_ruleset` | Which rules apply |
| `live_check` | Checks one file |
| `get_open_issues` | Results of the last full scan |
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

**Open question:** the README does not say how to trigger a full repository scan (as opposed to `live_check` on one file). Check the Norma dashboard or ask the QualityClouds mentors before 22:00.

## Sources

- https://github.com/qualityclouds/norma-mcp (README, `mcp.json`, `skills/norma-workflow/SKILL.md`)
