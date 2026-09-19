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
| Official forest-fire incidents across Spain, and the official closures near the selected fire | The DGT's DATEX II feed on its National Access Point, refreshed every 5 minutes | `GET /api/live/dgt`, `dgt` in the operations answer; navy warning triangles on the map and "Official DGT closures and incidents" in the group |
| The alert drafts as one CAP 1.2 file, status Draft | Backend, from the same drafts, in Spanish and English | `GET /api/live/operations/{fire_id}/cap`, the "Download drafts as CAP (XML)" button |

Select a fire by tapping it on the map, or pick it from the list of fires Deepfire has simulated. The map fits the fire and its places. See [Deepfire, live operations](../services/deepfire.md#live-operations-for-one-selected-fire) for how it works and what was verified.

It keeps working when a provider does not answer: the last Deepfire answer is kept in `data/live_spread.json`, the places of each run in `data/live_places/`, and the last DGT answer in `data/live_dgt.json`. A stale answer says so in the panel; a DGT outage never blocks the places at risk. See [DGT](../services/dgt.md).

## What it is, and what it is not

- **A prediction, not a fact.** Every time and every place comes from a simulation. The panel always says: "Prediction from Deepfire's ELMFIRE simulation, not an official warning. In a real emergency, follow 112 and Civil Protection."
- **Drafts, not warnings.** Nothing is sent to anyone. There is no public alerting channel in HackFire. The CAP file says `Draft`, never `Actual`.
- **Official and suggested roads stay apart.** The DGT's closures are official data, labelled as such with their source; the roads to close are HackFire's suggestion from the simulation. Most DGT closures near a fire are roadworks, and the panel shows their cause.
- **Times count from the run.** Deepfire starts a run from the latest observations when it creates it. The older the run, the less the times say about now; the panel shows when the run was made.
- **OpenStreetMap is uneven.** Some care homes or schools have no name, some housing estates are not mapped, and towns and villages are OSM points padded to a rough size (150 m for a hamlet to 2 km for a city), not their boundaries.
- **Main roads only.** Trunk, primary and secondary roads with a number, as in the replay. Motorways and local roads are not listed.
- **No run, no places.** A fire Deepfire has not simulated shows no places at risk.

## What does not work yet

- **Real residents.** Live mode has no registry of who lives in the places at risk, so it lists no residents.
- **Calls.** The voice agent calls residents only in the replay, with sample residents. Calling in a real fire needs that registry.
- **Public alerts.** ES-Alert and SMS to a zone are run by Civil Protection and the regional emergency services. HackFire only drafts the text, and hands it over as a CAP file.
- **Official evacuation plans.** The replay's safe points and crew base are the team's assumptions, not official meeting points or shelters.
- **Road closures in live mode** are the simulation's suggestion, shown next to the DGT's official ones. The coordinator's own closures (a tap on the map) belong to the replay, where they work offline: with #66, a closure keeps a cached route that avoids it, and otherwise the route says the usual way is cut. Official closures do not change any route yet.

## From a demo to an ongoing emergency

A short roadmap. Step 1 is built, and so are the audit log of step 2, the first part of steps 5 and 6, and the monitoring of step 7.

1. **Live incident (this change).** Any active fire in Spain gets Deepfire's ELMFIRE prediction, the places at risk with their time to impact, draft alerts per zone, and the roads to close. Nothing is sent.
2. **Persistent, multi-user state.** A database instead of in-memory state, and coordinator accounts. **The audit log exists now, without a database:** every order, call, campaign, status report (with its source: voice agent, typed answer, button, simulation or safety net), crew alert, road closure, video link, simulation toggle and reset is appended to `data/audit.jsonl`, read back after a restart, never with a phone number. The dashboard shows the latest events in *Activity log* with a JSON download (`GET /api/audit`, [operations](../setup/operations.md)). Still missing: who did it (no accounts) and a store shared by several backends.
3. **Residents.** A registry from the emergency services or the municipality (the municipal register, or the vulnerable-person registries in civil protection plans), on a GDPR legal basis of vital or public interest, with geocoded addresses, imported per incident area.
4. **Telephony.**
   - A SIP trunk with Spanish numbers attached to the SLNG agent (SLNG's "Manual" outbound connection: termination host, SIP credentials, a caller-ID number).
   - An official, recognisable caller ID.
   - Capacity for concurrent calls, retries when nobody answers, and transcripts stored with each status.
5. **Public alerts.** ES-Alert and zone SMS stay with Civil Protection and the regional emergency services. HackFire's drafts would feed their system; it would not send them itself.
   - *Built:* the drafts download as one CAP 1.2 document, status `Draft`, in Spanish and English, one area per place (see [below](#alert-drafts-as-cap-12)).
   - *Not built:* any connection to an alerting system, a review and sign-off step, and the extensions a given system asks for (geocodes, its own event codes).
6. **Evacuation plans.** Official safe points and shelters from municipal and regional plans, as data, instead of the nearest-town heuristic. Road closures from official traffic feeds as well as the coordinator's taps.
   - *Built:* the DGT's forest-fire incidents and road or carriageway closures, read live from its DATEX II feed, on the map and next to the selected fire ([DGT](../services/dgt.md)).
   - *Not built:* routes that avoid the official closures, the regions with their own traffic authority (Catalonia, the Basque Country), which this feed may not fully cover (not checked), and official safe points and shelters.
7. **Model and operations.** ELMFIRE is already physics-based; validate it against observed perimeters, and run a pilot with one municipality. **Monitoring exists now:** `GET /api/status/providers` and the *Service status* group say whether Deepfire, openrouteservice, Overpass, SLNG, Twilio and Vonage answer, with a reason, such as "quota spent: using the cached routes" when openrouteservice's daily quota runs out ([operations](../setup/operations.md)). The fallbacks when a provider is down were already there. Still missing: alerting someone when a service goes down, and the DGT feed in the list.

## Alert drafts as CAP 1.2

The Common Alerting Protocol ([OASIS CAP 1.2](http://docs.oasis-open.org/emergency/cap/v1.2/CAP-v1.2-os.html)) is the format public alerting systems exchange, ES-Alert and EU-Alert among them. `GET /api/live/operations/{fire_id}/cap` (`backend/app/cap.py`) turns the selected fire's alert drafts into one CAP document, and the panel downloads it with "Download drafts as CAP (XML)": "Standard alert format, ready to hand to Civil Protection. Status: draft, not sent."

| Element | Value |
|---|---|
| `status` | Always `Draft`, never `Actual` |
| `msgType`, `scope`, `sender`, `sent` | `Alert`, `Public`, `hackfire`, now (UTC written `-00:00`, as CAP requires) |
| `note`, `incidents` | "Draft written by HackFire from a simulation. Not sent." in both languages; the Deepfire fire id |
| `info` | One per backend locale, the residents' language first: `es-ES`, then `en-GB` (`cap.language` in `backend/app/locales/`) |
| `category`, `event` | `Fire`, "Incendio forestal" / "Wildfire" |
| `urgency` | `Immediate` when the simulation reaches a place within the hour, else `Expected` |
| `severity`, `certainty` | `Severe`, `Likely` |
| `expires` | The end of the run (run time plus its duration) |
| `headline`, `description`, `instruction` | The first place and how many more; the run and the caveat, then each draft; follow Civil Protection and 112 |
| `area` | One per drafted place: `areaDesc` its name, a `polygon` per part of its outline (lat,lon pairs, simplified to about 50 m, closed) or a 200 m `circle` for a point |

A fire with no drafts has no button and the endpoint answers 404. Tests check that the document is well-formed, that `status` is `Draft`, and the element order of the CAP 1.2 schema (`backend/tests/test_live_operations.py`); the schema itself is not in the repo. Verified on 2026-09-19 at about 22:37 CEST with the Vitoria-Gasteiz (Álava) run: 5 areas in each of two `info` blocks, and the file validated against the official `CAP-v1.2.xsd` with a one-off `xmlschema` run outside the project.
