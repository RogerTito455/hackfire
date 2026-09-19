# What works for a real fire

HackFire has two modes. The **replay** shows the whole flow on the 23 July 2026 fire, with sample residents and calls. **Live** runs on the fires burning in Spain right now. This page says what live mode does for any real fire today, what it does not do, and what stands between the demo and use in an ongoing emergency.

## What works today, for any fire burning in Spain

| What | Source | Where |
|---|---|---|
| Active fires, refreshed every minute | Deepfire's active clusters over Iberia | `GET /api/live/fires`, the map in live mode |
| Predicted spread for the next 12 h, hour by hour | Deepfire's own ELMFIRE runs (terrain, fuel, weather), made automatically; HackFire never queues one | `GET /api/live/spread`; 74 of 141 active fires had a run on 2026-09-19 at 20:40 CEST |
| For one selected fire: the places at risk and when the simulation reaches each | OpenStreetMap through Overpass, intersected with the run's hourly polygons | `GET /api/live/operations/{fire_id}`, the *Places at risk* group in the sheet |
| Alert drafts per place, soonest first | Backend templates in English and Spanish | Same group, each labelled "Draft, not sent" |
| Roads to close to residents (the simulation reaches them within the hour; crews still use them) | Same rule as the replay | Same group, and a dashed red cordon on the map |

Select a fire by tapping it on the map, or pick it from the list of fires Deepfire has simulated. The map fits the fire and its places. See [Deepfire, live operations](../services/deepfire.md#live-operations-for-one-selected-fire) for how it works and what was verified.

It keeps working when a provider does not answer: the last Deepfire answer is kept in `data/live_spread.json`, and the places of each run in `data/live_places/`. A stale answer says so in the panel.

## What it is, and what it is not

- **A prediction, not a fact.** Every time and every place comes from a simulation. The panel always says: "Prediction from Deepfire's ELMFIRE simulation, not an official warning. In a real emergency, follow 112 and Civil Protection."
- **Drafts, not warnings.** Nothing is sent to anyone. There is no public alerting channel in HackFire.
- **Times count from the run.** Deepfire starts a run from the latest observations when it creates it. The older the run, the less the times say about now; the panel shows when the run was made.
- **OpenStreetMap is uneven.** Some care homes or schools have no name, some housing estates are not mapped, and towns and villages are OSM points padded to a rough size (150 m for a hamlet to 2 km for a city), not their boundaries.
- **Main roads only.** Trunk, primary and secondary roads with a number, as in the replay. Motorways and local roads are not listed.
- **No run, no places.** A fire Deepfire has not simulated shows no places at risk.

## What does not work yet

- **Real residents.** Live mode has no registry of who lives in the places at risk, so it lists no residents.
- **Calls.** The voice agent calls residents only in the replay, with sample residents. Calling in a real fire needs that registry.
- **Public alerts.** ES-Alert and SMS to a zone are run by Civil Protection and the regional emergency services. HackFire only drafts the text.
- **Official evacuation plans.** The replay's safe points and crew base are the team's assumptions, not official meeting points or shelters.
- **Road closures in live mode** are the simulation's suggestion. The coordinator's own closures (a tap on the map) belong to the replay, where they work offline: with #66, a closure keeps a cached route that avoids it, and otherwise the route says the usual way is cut.

## From a demo to an ongoing emergency

A short roadmap. None of it is built beyond step 1.

1. **Live incident (this change).** Any active fire in Spain gets Deepfire's ELMFIRE prediction, the places at risk with their time to impact, draft alerts per zone, and the roads to close. Nothing is sent.
2. **Persistent, multi-user state.** A database instead of in-memory state, coordinator accounts, and an audit log of every order, call and status change.
3. **Residents.** A registry from the emergency services or the municipality (the municipal register, or the vulnerable-person registries in civil protection plans), on a GDPR legal basis of vital or public interest, with geocoded addresses, imported per incident area.
4. **Telephony.**
   - A SIP trunk with Spanish numbers attached to the SLNG agent (SLNG's "Manual" outbound connection: termination host, SIP credentials, a caller-ID number).
   - An official, recognisable caller ID.
   - Capacity for concurrent calls, retries when nobody answers, and transcripts stored with each status.
5. **Public alerts.** ES-Alert and zone SMS stay with Civil Protection and the regional emergency services. HackFire's drafts would feed their system; it would not send them itself.
6. **Evacuation plans.** Official safe points and shelters from municipal and regional plans, as data, instead of the nearest-town heuristic. Road closures from official traffic feeds (for example the DGT's open incident data) as well as the coordinator's taps.
7. **Model and operations.** ELMFIRE is already physics-based; validate it against observed perimeters. Add monitoring, fallbacks when a provider is down (as the demo already does), and a pilot with one municipality.
