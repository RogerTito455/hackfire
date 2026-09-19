# Development workflow

How the three of us build HackFire without stepping on each other. Scope and schedule are in [PLAN.md](../../PLAN.md); this page is the day-to-day routine.

## Work comes from the issues

Every piece of work is a GitHub issue. Core work is written as **slices**: each one cuts through every layer it needs (data, backend, frontend) and ends in something you can see on the dashboard. The `owner:*` label says who drives it.

```bash
gh issue list --label core                  # the core slices
gh issue list --label owner:bryan           # yours
gh issue view 3                             # the "Done when" checklist is the definition of done
```

Build order follows the dependencies written in each issue:

```
#1 Access (keys, phone number)
 ├─ #2 Slice 1  deployed skeleton ─────────────┐
 ├─ #3 Slice 2  hotspot replay + time slider   │
 │   ├─ #4 Slice 3  spread + zones at risk     │
 │   │   └─ #5 Slice 4  lead time              │
 │   └─ #11 Slice 10 live mode                 │
 ├─ #6 Slice 5  routes (hand-drawn fire polygon until #4 lands)
 └─ #7 Slice 6  agent changes a pin  ◄─────────┘   ← checkpoint Saturday 18:00
     ├─ #8 Slice 7  call campaign
     │   └─ #9 Slice 8  crew notification (+ route from #6)
     └─ #10 Slice 9 coordinator asks by voice (+ #6)
```

Extensions (#17 Norma, #18 Vonage, #19 Devin) start only after checkpoint 2 at 19:30 says the four steps work end to end. Anything not in PLAN.md section 4 gets raised with the team before anyone builds it.

## Branches and commits

- Short-lived branch per slice: `slice-2-hotspot-replay`, `fix-cors`. Merge to `main` the same afternoon; `main` deploys.
- Commit messages in English, imperative mood: "Render hotspots as a MapLibre layer".
- Reference the issue: `Closes #3` in the pull request, or `Refs #3` for partial work.
- `pnpm check` passes before every commit.

## Rules the code depends on

These are in [CLAUDE.md](../../CLAUDE.md); the short version:

- **UI is independent of logic.** `frontend/src/ui/` takes props and renders. Logic goes in `domain/` (pure) and `hooks/` (stateful). HTTP only in `services/`.
- **Third parties only in `backend/app/providers/`**, environment only in `backend/app/config.py`.
- **The tool contract is shared.** Changing a request or response model in `backend/app/models.py` means updating `frontend/src/domain/triage.ts` and telling the team in the chat.
- **Stubs are explicit:** `stub: true` plus a `TODO(map|voice|data)` comment. Remove both when the real thing lands.
- **Demo mode first.** Anything slow or external is fetched once and cached under `data/`. The live demo must not wait on a third-party API.
- **Manifests change through commands** (`pnpm add`, `pnpm pkg set`, `uv add`), never by hand.

## Documenting as you go

- Hit a surprise (an API that behaves differently from its docs, a limit, a workaround)? Write a finding: `docs/findings/YYYY-MM-DD-<slug>.md`, and link it from the service page.
- Got a service working? Update its page in `docs/services/` with the command or request that worked, and flip its status.
- Numbers for the pitch (lead time, voice latency) go in a finding with how they were computed.
