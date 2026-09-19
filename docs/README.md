# HackFire docs

Everything the team learns while building HackFire. [PLAN.md](../PLAN.md) stays the source of truth for scope, schedule and decisions; these pages cover *how*: setting up, using each service, and what we found out along the way.

## Map

| Section | Page | What it answers |
|---|---|---|
| **Setup** | [New machine](setup/new-machine.md) | From a fresh laptop to a running dashboard |
| | [Environment variables](setup/environment.md) | Every key: what reads it, where to get it |
| | [Claude Code](setup/claude-code.md) | MCP servers and skills for AI-assisted development |
| | [Deployment](setup/deployment.md) | The one Railway service that serves the API and the dashboard |
| **Services** | [Deepfire](services/deepfire.md) | Hotspots, active fires, spread simulation |
| | [SLNG](services/slng.md) | Voice agent, outbound calls, SMS |
| | [openrouteservice](services/openrouteservice.md) | Evacuation and rescue routes |
| | [Overpass (OpenStreetMap)](services/overpass.md) | Towns, care homes, schools, health centres and roads for the zones at risk |
| | [Supabase](services/supabase.md) | Hosted Postgres; not adopted, see the page |
| | [Vonage Video](services/vonage.md) | Extension 2: live video from a resident who needs rescue |
| | [Norma (QualityClouds)](services/norma.md) | Extension 1: scan, fix, rescan |
| | [Devin (Cognition)](services/devin.md) | Extension 3: self-improving spread model |
| **Demo** | [Runbook](demo/runbook.md) | Before the demo, and what to do when something fails on stage |
| | [Pitch script](demo/pitch.md) | The three minutes, the checked figures, questions to prepare |
| **Development** | [Workflow](development/workflow.md) | Slices, branches, checks, the tool contract |
| **Design** | [DESIGN.md](../DESIGN.md) | Colours, type, the mobile layout, old-browser rules, languages |
| | [Icons](../frontend/src/ui/icons/README.md) | The hand-drawn icon set: format rules, map markers, catalogue |
| **Findings** | [Findings log](findings/README.md) | Things we learned the hard way, dated |

## Adding a page

- **One topic per file**, in the section it belongs to. A new external service gets `services/<name>.md` built from the template below; a new finding gets `findings/YYYY-MM-DD-<slug>.md`.
- **Link it from this table**, and from the section index if there is one.
- **Write in English**, short and concrete: commands in code blocks, every external claim with a link to its source.
- **No secrets, no phone numbers, no content from `NOTES.internal.md`.** Name the variable, never its value.
- **Say what is verified.** If a command or endpoint has not been run yet, write "not yet run" next to it.

### Service page template

```markdown
# <Service>

**Used for:** <which step or slice in PLAN.md>
**Status:** not started | in progress | working | extension (not started)
**Owner:** <name>

## Access
Sign-up link, which variables to set (see setup/environment.md).

## In the app
Which module calls it (always under backend/app/providers/), and which endpoints.

## In Claude Code
MCP server, if any, and how to add it.

## Gotchas
Limits, errors, surprises. Link each to a finding if there is one.

## Sources
```
