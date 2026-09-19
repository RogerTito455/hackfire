# HackFire — Agreed Plan

HackBarna 2026 · 19–20 September · Norrsken House Barcelona
Main challenge: **Norrsken / Deepfire "AI for Wildfire", track 4 "Values at risk"**
Core sponsors: **SLNG** (voice) and **Nebius Token Factory** (LLM)
Team: 2 developers + 1 ML / data profile

This document records what the team agreed during Saturday's decision session. It is the source of truth for scope: anything not listed under "Core" does not get built until the core works end to end.

---

## 1. The idea in one sentence

A voice agent that **calls residents before the fire reaches them**, tells them which way to leave, and asks whether they can get out on their own. From their answers, the emergency coordinator sees on a map who is evacuating by themselves, who is not answering, and **who needs rescue** — so firefighters only go where they are truly needed.

> "Every resident who evacuates on their own is a rescue the firefighters don't have to make."

## 2. The problem

On 23 July 2026 the Burgohondo wildfire (Ávila), the largest in Spain, ran 3 km in 40 minutes and reached the La Atalaya housing estate (El Tiemblo). Between 1,200 and 1,300 people were evacuated, 5 homes were destroyed, and a care home for the elderly was evacuated at night. In total, more than 13,000 people were evacuated or confined.

Public alerting today has three gaps:

1. **It is one-way.** ES-Alert broadcasts the same message to a whole area and does not listen. The coordinator does not know who got the message, who has already left, or who cannot move.
2. **It is not personal.** It does not tell each resident how to get out from their own home, whether on foot or by car, or which roads the fire is about to cut.
3. **Rescues are discovered late.** Elderly people, people without a car and people who are trapped surface only when someone calls 112, with the lines saturated and crews already committed.

The result: firefighters spend resources locating and extracting people instead of fighting the fire.

**A limitation we acknowledge:** in that fire, 16 municipalities lost mobile coverage. A phone call needs a network, exactly as ES-Alert does. Our answer: calls are triggered by the **prediction**, hours before the fire arrives, while the cell towers still work; and the "no answer" state tells the coordinator which homes need a patrol sent to them.

## 3. The solution: four steps

1. **The fire and where it is heading.** Deepfire satellite hotspots on the map, with a time slider, and an hour-by-hour predicted spread cone. Two modes on the same code: **live** (fires active right now, queried from the Deepfire API) and **replay** (static extract of 23 July, which is where the full flow is demonstrated).
2. **Who is in its path.** The spread is intersected with towns, housing estates, care homes, schools and roads (OSM). Each zone gets an estimated time to impact.
3. **The agent calls residents in the at-risk zones** (SLNG). It gives them their exit route, on foot or by car, avoiding the predicted fire, and asks: "Can you leave on your own? How many of you are there? What can you see from there?"
4. **Triage on the coordinator's dashboard.** Each resident ends up in one of three states: *evacuating*, *no answer* or *needs rescue*. Rescues are ranked by time to impact and vulnerability, each with its route. **Every new rescue is pushed to the fire crew** by SMS or call, with the location and a link to the route. The coordinator — or a firefighter by phone — can ask by voice: "Which rescues do I have, and in what order?"

### How the team's notes map to the plan

| Note | Status | Where it lives |
|---|---|---|
| Real time observability using Deepfire API | Included | Step 1: map with time slider, on top of the Deepfire API |
| Satellite datasets (small, for the demo) | Included | Static extract of 22–24 July hotspots, committed to the repo |
| Based on live fires and spreading | Included, with a nuance | Step 1: live mode with Deepfire's active fires. The full calling flow is shown in replay, because on Sunday there may be no active fire in the area |
| Send notifications to citizens | Included | Step 3: the outbound call is the notification |
| Send notifications to firefighters | Included (added) | Step 4: SMS or call to the crew for every new rescue |
| Cities / towns involved | Included | Step 2: at-risk zones with time to impact |
| Evacuation route (walking, car) | Included | Step 3: openrouteservice walking and driving profiles |
| Declare a place in danger / fire spreading | Included | Step 3: what the resident says on the call becomes an observation pin. If we get a phone number, residents can also call the agent themselves |
| Whether someone needs help (keywords) | Included, with a change | Step 4: classified by the LLM, not by a keyword list — more robust with real speech |
| Rescue, evacuation | Included | Step 4: prioritised rescue queue |
| Volunteers (nearby notifications) | **Out of core** | Mentioned in the pitch as a next step |
| Tools, materials | **Out of core** | Same as volunteers |

On volunteers: sending untrained people towards a wildfire is a serious risk. If built later, it must be logistics support away from the fire front, and always under the coordinator's orders.

## 4. Scope

**Core (the only thing built until it works end to end):** the four steps above, over a box of roughly 15 km around El Tiemblo and La Atalaya, replaying 23 July 2026.

**Extensions, in this order, and only if everything before works:**

1. **Norma (QualityClouds):** one scan, one fix, one rescan of the repo. About 45 minutes. Covers "validate for production".
2. **Vonage Video:** a resident in the "needs rescue" state gets an SMS with a link, opens their camera in the browser, and the coordinator sees them on the dashboard, anchored to the map, with live captions. 2 to 3 hours. Go/no-go at 19:30.
3. **Devin (Cognition):** iterate the spread model against the real hotspots, with an IoU-style metric as the validator. 3 hours or more. Most likely only mentioned in the pitch.

**Out:** early detection (Deepfire already does it), a generic alerts app, neighbourhood chat, photos to feed the AI, firefighting protocols, volunteers and materials, a second case in Huelva, Catalan (SLNG's catalogue lists it, but the demo residents speak Spanish; see `docs/findings/2026-09-19-slng-lists-catalan.md`).

## 5. The pitch number: lead time

With the hotspots available at time T, the system flags La Atalaya as at risk. The hotspots reach it at time T+X. **X is the lead time**, and it is the headline figure of the presentation.

It is computed from satellite data only. It claims nothing about when the authorities issued their warnings, because we do not have that time. No "we would have saved X" and no "we would have warned N hours before 112". People lost their homes two months ago.

## 6. Stack

| Piece | Technology | Notes |
|---|---|---|
| Fire data | Deepfire API (OGC Features, GeoJSON) with token | Downloaded once and stored as static files for the replay |
| Predicted spread | **Replay:** cone from the front's velocity over the last hours of hotspots (ML, ~2 h). **Live mode:** Deepfire fire-spread simulation | The documented simulation API seeds from at most 168 hours back and has no start-time field, so it cannot replay 23 July unless the Deepfire mentors offer another way. See `docs/findings/2026-09-19-deepfire-no-historical-simulation.md` |
| At-risk zones | OSM via Overpass, precomputed; shapely / geopandas | Time to impact = distance to front / rate of spread |
| Routing | openrouteservice, `avoid_polygons`, `driving-car` and `foot-walking` profiles | Max 200 km² and 20 km in height or width per polygon: clip the fire to a square of at most 14 km around the route. See `docs/findings/2026-09-19-ors-avoid-polygon-limit.md` |
| Voice | SLNG Agent Builder + Deepfire MCP + our own tools | 45-minute timebox; if it cannot call our tools or route to Nebius, build our own STT → LLM → TTS pipeline on the SLNG gateway |
| Calls and SMS | SLNG does not supply numbers: outbound calls need our own SIP trunk (e.g. Twilio) and SMS needs Twilio. Ask the mentors what they can lend us | Likely fallback: push-to-talk on the web, and crew notifications shown on the dashboard. Agent tools must be reachable over HTTPS, so deploy early. See `docs/findings/2026-09-19-slng-bring-your-own-number.md` |
| LLM | Nebius Token Factory (OpenAI-compatible API) | Structured extraction from the call, and the agent's reasoning |
| Backend | FastAPI (Python) | One service; state in SQLite or in memory |
| Dashboard | React + MapLibre GL or Leaflet | Updates by polling every 2 s, or SSE |
| Deployment | One Railway service: FastAPI serves the API, the agent tools and the built dashboard, from the root `Dockerfile` | The demo runs against the public URL. Why not Vercel or Cloudflare Workers: `docs/setup/deployment.md` |

### Agent tool contract

This is the interface between voice and everything else. Fix it in the first hour.

- `get_fire_status(zone)` → state of the front and time to impact
- `get_evacuation_route(address, mode)` → walking or driving route that avoids the predicted fire
- `report_status(neighbor_id, status, people, mobility, observation)` → updates triage and creates the pin
- `get_rescue_queue()` → rescues ranked by priority
- `get_rescue_route(rescue_id)` → route for the crew

## 7. Procedure and schedule

### Saturday

| Time | What | Who |
|---|---|---|
| 14:00–15:00 | Public repo, deployed skeleton, keys (Deepfire, SLNG, Nebius, ORS). Download 22–24 July hotspots for the box `-4.85,40.30,-4.40,40.50` and commit them. Run one Deepfire simulation for 23 July and cache the result. Fix the tool contract and the work split | Everyone |
| 15:00–18:00 | **Map track:** map, time slider, hotspot and cone layers, pins with the three states, routes. **Voice track:** SLNG agent (45-min timebox), backend with the five tools, LLM on Nebius, outbound call. **Data track:** spread, at-risk zones from OSM, time to impact, rescue priority, lead-time calculation | In parallel |
| **18:00** | **Checkpoint 1:** a real call changes a pin on the deployed dashboard. If not, the whole team focuses on that | Everyone |
| 18:00–19:30 | Coordinator's voice query, rescue queue, mock registry of 8–10 residents with real La Atalaya addresses and the team's own phones. Crew notification for each new rescue (30 min max). Live mode with Deepfire's active fires (45 min max) | Everyone |
| **19:30** | **Checkpoint 2:** do all four steps work end to end? Yes → start Vonage. No → Vonage is dropped, no discussion | Everyone |
| **21:00** | **Feature freeze.** The presenter stops coding and writes the script. Demo mode: cached simulation, push-to-talk, pre-recorded audio, text box as backup. Measure voice latency per turn (SLNG asks for real numbers) | Everyone |
| 22:00 | Norma: scan, fix, rescan. README. **Record the 60-second backup video** | 1 + 1 |
| 23:00 | Venue closes | |

### Sunday

| Time | What |
|---|---|
| 9:00–11:00 | Rehearse the demo at least five times, with a stopwatch. Bug fixes only; nothing new |
| **11:00** | **Code submission** (confirmed by the team) |
| 14:00 | Demos |

## 8. Demo script (about 3 minutes)

1. **The problem (20 s).** 23 July, Burgohondo, 3 km in 40 minutes. The warning reaches everyone the same way, and nobody knows who needs help.
2. **The dashboard (40 s).** Move the time slider. The cone reaches La Atalaya and the system flags it at risk with X minutes of lead time.
3. **The call (60 s).** A phone rings in the room. The agent gives the driving route and asks whether they can leave. Answer: "My mother can't walk." The pin turns red on the dashboard, and the crew gets the notification.
4. **The coordinator (30 s).** Asks by voice: "Which rescues do I have, and in what order?" The agent answers and draws the route.
5. **Close (30 s).** The lead-time number, the coverage objection raised by us before the jury does, and next steps: live video, volunteers, self-improvement with Devin.

## 9. Risks

| Risk | Mitigation |
|---|---|
| Voice fails in a noisy room | Push-to-talk, pre-recorded audio, text box, backup video |
| Deepfire returns 503 (shared capacity) or is slow | Everything from Deepfire cached as static GeoJSON |
| A simulation call fails during the build | Fallback cone from front velocity |
| No phone number from the mentors | Inbound call through the web |
| SLNG Agent Builder cannot call our tools | Own pipeline after 45 minutes |
| Scope grows again | This document. Checkpoints at 18:00 and 19:30 |
| Jury question: "why not ES-Alert?" | ES-Alert broadcasts and does not listen; this holds a conversation with each resident and feeds information back to the coordinator. It is complementary |
| Misattributed press quotes | Check every figure against the original source before it goes on a slide |

## 10. Decisions

**Confirmed by the team**

- Idea: wildfires, track 4. Goal: overall prize and sponsor prizes at the same time.
- Citizens are the priority, framed as triage so that it also serves first responders.
- Demo case: 23 July 2026, the run towards La Atalaya. The team confirms it has the historical data.
- Voice with the SLNG Agent Builder, the Deepfire MCP and our own tools.
- Phone number: ask the SLNG mentors.
- Full hardened demo mode.
- Lead time as the headline figure. The coverage objection is raised in the pitch.
- Norma at the end. Devin, later.
- Project name: **HackFire**.
- The team organises the work split itself.
- The Deepfire simulation works over Spain. (The team also understood it could replay 23 July; the API docs contradict that, so it is listed under Open until the mentors settle it.)
- One project can enter several challenges at once.
- Crew notification for every new rescue, and a live mode in addition to the replay.
- Code submission is Sunday at 11:00.
- All project documentation is written in English.

**Adopted on recommendation, not yet confirmed — review them in five minutes**

- The agent initiates the call (outbound), not the resident.
- Mock registry of 8–10 residents; in the pitch, "voluntary municipal registry, complementary to ES-Alert".
- The firefighter has no interface of their own: they use the same voice agent by phone.
- Vonage is an extension with a 19:30 cut-off; separately, a backup video is recorded tonight.
- Devin is the last extension.
- The coordinator approves the call campaign before the agent starts dialling (human in the loop, borrowed from Watch Duty).
- The agent can pass on a **confinement** order as well as an evacuation route. In the two recent Catalan fires we checked (Torrefeta and Paüls, 2025) the official order was to stay inside, not to leave.

**Open**

- Can Deepfire produce a spread for 23 July 2026 some other way (internal parameter, a run from the web app, an existing `auto: true` run)? Ask the mentors. Until then the replay uses the front-velocity cone.
- What can the SLNG mentors lend us: a number on their trunk, Twilio credentials, or nothing?
- Who presents: decide before 21:00, which is when that person stops coding.

## 11. Reference products: Watch Duty and focs.cat

Researched on 19 September 2026. focs.cat is a single-page app, so its details were read from its public JavaScript bundle and the app stores rather than the rendered page.

| Criterion | Watch Duty (US) | focs.cat (Catalonia) |
|---|---|---|
| Operator | Non-profit (Sherwood Forestry Service), founded 2021 | Private, unofficial project (Gendant) |
| Source and verification | 911 dispatch, radio, cameras and satellites, **verified by human reporters** before any alert | @bomberscat posts and the Bombers ArcGIS feed, **parsed by AI, no human verification**, with a deliberate 10–15 minute delay |
| Update speed | Minutes; no published SLA | 10–15 min delay plus ~3 min sync; store reviews report stale incidents |
| Notifications | Push by county or location, **only when life or property is threatened** | Push by municipality or county, for every fire |
| Map | Perimeters, evacuation zones and orders, shelters, wind, cameras | One point per fire, plus wind and risk layers; no perimeter, no evacuation information |
| Tells the citizen what to do | Partly: shows orders and shelters, but not "your route" | No |
| Two-way communication | No (photo upload only) | No |
| Use for first responders | Yes, with the Pro tier | Marginal: resource counts only |
| Coverage | All 50 US states | Catalonia |

A possible example of the cost of unverified AI parsing: the focs.cat incident `focs.cat/fire/1522331` appears in Deepfire under the name "Manresa", but focs.cat places it in Las Peñas de Riglos (Huesca, Aragon) and marks it as a false alarm. That it is a geocoding error is our inference; check it before using it in the pitch.

Official Catalan channels (the Bombers map refreshed every 10 minutes, the Pla Alfa map, ES-Alert, @emergenciescat, My112) are also one-way. None gives a personal route, and the only way a resident can talk back is by calling 112.

**What HackFire borrows from Watch Duty**

1. The alert threshold: contact people only when there is a threat to life or property. No noise.
2. A per-fire timeline where every update carries a timestamp and a source.
3. Zone-based targeting, passing on the official order in plain language.
4. A human in the loop before anything goes out at scale: the coordinator approves the call campaign.

**The gap both leave, which HackFire covers**

- Both are pull-based, one-way, and need a smartphone with data. Neither reaches an elderly resident with a landline.
- Neither gives a personal instruction ("stay inside" or "leave by road X").
- Neither tells the coordinator who cannot move.

**What we do not try to copy in ten hours:** the reporter network and radio monitoring, live perimeters and cameras, aircraft tracking, native apps with push, multi-hazard coverage.

## 12. Sources

- Challenges and criteria: https://www.hackbarna.com/en/events/aisummit26 · https://deepfire.co/hackbarna
- Deepfire API: https://docs.deepfire.co/llms.txt · MCP without a token: `https://api.deepfire.co/mcp`
- SLNG: https://docs.slng.ai/llms.txt · Nebius: https://docs.tokenfactory.nebius.com/quickstart
- openrouteservice, `avoid_polygons`: https://giscience.github.io/openrouteservice/api-reference/endpoints/directions/routing-options
- Norma (MCP): https://github.com/qualityclouds/norma-mcp
- Watch Duty: https://www.watchduty.org/how-it-works/overview · https://en.wikipedia.org/wiki/Watch_Duty
- focs.cat: https://focs.cat · https://play.google.com/store/apps/details?id=cat.focs
- Official Catalan channels: https://interior.gencat.cat/plaalfa · https://govern.cat/salapremsa/notes-premsa/529522/
- Burgohondo wildfire: https://www.tribunaavila.com/noticias/453214/el-incendio-de-burgohondo-deja-1-500-evacuados-y-arrasa-gran-parte-del-valle-iruelas · https://avilared.com/art/93361/incendio-devastador-burgohondo-iruelas-1500-evacuados-cinco-casas-quemadas · https://avilared.com/art/93357/alerta-esalert-confinamiento-el-tiemblo-burgohondo-navaluenga-incendio-forestal · https://theobjective.com/tecnologia/2026-07-29/fallos-comunicacion-incendio-almeria-madrid-avila/
