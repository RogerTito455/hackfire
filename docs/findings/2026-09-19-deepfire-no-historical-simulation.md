# The Deepfire spread API cannot simulate a past date

**Date:** 2026-09-19 · **Area:** Deepfire, slice 3 (#4)

## What happened

PLAN.md assumes we can run a Deepfire spread simulation for the 23 July 2026 run towards La Atalaya and cache it. The documented request body for `POST /v1/fire-spread/simulations` has no start-time, as-of or historical field:

- `clusterId` or `latitude`/`longitude`
- `durationHours` (1–24), `model`, `ensembleMembers`, `sources`
- `lookbackHours` (1–168): "only hotspots within this timeframe seed the simulation", counted back from now

Unknown fields are rejected with 422. So seven days is the furthest back a simulation can be seeded, and 23 July is two months ago.

Not verified against the live API: nobody has run a simulation yet.

## What we do about it

1. **Ask the Deepfire mentors** whether a past run is possible some other way: an internal parameter, or a run from the web app.
2. **Check for an existing run**: `GET /v1/fire-spread/simulations?since=…` lists the organisation's runs, including ones Deepfire made automatically (`auto: true`) on fires in its jurisdiction.
3. **If neither works, go straight to the fallback** already in PLAN.md: a cone from the front's velocity over the last hours of hotspots. The replay hotspots themselves are fine; the hotspot history goes back to January 2025.
4. A live simulation still works for **live mode** (#11), on a fire burning now.

The team had confirmed that the simulation "has the history needed for 23 July" (PLAN.md section 10). This finding contradicts the docs, not necessarily that confirmation; settle it with the mentors before anyone spends hours on it.

## Sources

- https://docs.deepfire.co/api/fire-spread
- https://docs.deepfire.co/reference/fire-spread/simulations/create-simulation
