# Findings

Things we learned that someone else on the team would otherwise have to learn again: API behaviour that differs from the docs, limits, data quirks, workarounds, and the numbers that go into the pitch.

One file per finding, named `YYYY-MM-DD-<slug>.md`, newest first in the list below.

| Date | Finding | Area |
|---|---|---|
| 2026-09-19 | [Which press figures hold up against their sources](2026-09-19-press-figures.md) | Pitch |
| 2026-09-19 | [Which LLMs an SLNG agent accepts for Spanish in Europe](2026-09-19-slng-agent-llms-for-spanish.md) | SLNG |
| 2026-09-19 | [SLNG passes a tool's arguments to our backend unchecked](2026-09-19-slng-tool-arguments-unchecked.md) | SLNG |
| 2026-09-19 | [Sending everyone to one safe point walked some residents into the fire](2026-09-19-evacuation-destinations.md) | Routes |
| 2026-09-19 | [The route cache did not cover every place a coordinator can order a zone to](2026-09-19-route-cache-coverage.md) | Routing |
| 2026-09-19 | [The lead time for La Atalaya: 6 h 8 min, and how it was computed](2026-09-19-lead-time.md) | Pitch figure |
| 2026-09-19 | [The replay spread is a cone from the front's velocity, and how it behaves on 23 July](2026-09-19-spread-cone-model.md) | Predicted spread |
| 2026-09-19 | [Railway configures a pnpm workspace as its frontend package](2026-09-19-railway-pnpm-workspace-import.md) | Deployment |
| 2026-09-19 | [New Railway services cannot use `railway.toml`](2026-09-19-railway-config-as-code-deprecated.md) | Deployment |
| 2026-09-19 | [Where La Atalaya is, and how close the hotspots get](2026-09-19-la-atalaya-location.md) | Replay data |
| 2026-09-19 | [SLNG's catalogue now lists Catalan](2026-09-19-slng-lists-catalan.md) | SLNG |
| 2026-09-19 | [The Deepfire spread API cannot simulate a past date](2026-09-19-deepfire-no-historical-simulation.md) | Deepfire |
| 2026-09-19 | [SLNG does not provide phone numbers, and its tools need HTTPS](2026-09-19-slng-bring-your-own-number.md) | SLNG |
| 2026-09-19 | [Clipping the fire to the demo box is not enough for openrouteservice](2026-09-19-ors-avoid-polygon-limit.md) | openrouteservice |
| 2026-09-19 | [Local setup: `pnpm setup` is a pnpm built-in, and the backend was not reading `.env`](2026-09-19-local-setup.md) | Setup |

## Template

```markdown
# <One-line finding>

**Date:** YYYY-MM-DD · **Area:** <service or part of the app> · **Found by:** <name>

## What happened
What we expected, what we got. Exact error text if short.

## Why
The cause, if verified. Otherwise say "not verified".

## What we do about it
The fix, workaround or decision, with links to the commit or issue.

## Sources
```

Pitch figures need extra care: say how the number was computed and from which data, and check any press figure against its original source before it reaches a slide.
