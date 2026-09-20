# The demo's workflow: what happens, what is real, what is weak

**Date:** 2026-09-19, after the feature freeze. Written to plan Sunday's rehearsal and decide what, if anything, still changes. [PLAN.md](../../PLAN.md) stays the source of truth for scope.

## The workflow today, end to end

1. **The fire.** The dashboard replays 22–24 July 2026 from cached Deepfire satellite hotspots (`data/`). The time slider sets the backend's replay clock (`POST /api/replay/time`), so what the agents are told follows the slider.
2. **Where it is going.** Every 30 minutes of 23 July a forecast is issued (`backend/app/spread.py`): the front's heading and speed from the last 3 hours of hotspots, projected hour by hour up to 6 h as a cone. It is cached in `data/spread_2026-07-23.geojson` ([finding](../findings/2026-09-19-spread-cone-model.md)).
3. **Who is in its path.** The cone is crossed with 68 places from OpenStreetMap: towns, estates, care homes, schools, health centres, roads. Each gets minutes to impact (`backend/app/impact.py`). La Atalaya is first flagged at 15:30 CEST: that is the **lead time**, 6 h 8 min before the first hotspot within 3 km ([finding](../findings/2026-09-19-lead-time.md)).
4. **The order.** One evacuation order per zone with residents. The proposal is the nearest safe point outside the forecast, or stay indoors. The coordinator approves it or picks another (`backend/app/orders.py`). Nobody is called before their zone's order is approved.
5. **The call.** The resident agent (SLNG, Nemotron Super, a Deepgram Aura 2 voice) starts with the fire, the order and the route by car already in its call data (`backend/app/briefing.py`). It gives the order and the route, asks three questions (can you leave on your own, how many are you, what do you see) and records the outcome with `report_status`.
   - **No phone line:** the call happens in the browser. The coordinator's laptop takes it and someone answers as the resident ("Llamar a … (contestas aquí)").
   - **Phone campaign:** exists but is off (`HACKFIRE_PHONE_CALLS`); it needs a SIP trunk on SLNG.
6. **Triage.** The outcome sets the resident's pin: evacuating, no answer or needs rescue.
   - **Rescues** are ranked by time to impact, then by the number of people.
   - **Crew alert:** each new rescue creates one, with a link to the crew route. It goes by SMS through Vonage (or Twilio, if that is ever set up) when a crew phone is configured, and is dashboard-only otherwise. The audit log says which: `alert.createdSms` or `alert.createdDashboard`.
   - **Crew plan:** assigns crews to rescues in order, and says whether each is in time.
7. **Routes.** Residents' routes avoid the burned area plus the next hour of predicted spread; crews' routes avoid only what has burned (openrouteservice, [finding](../findings/2026-09-19-evacuation-destinations.md)). They are cached for the scenario time.
8. **The coordinator's side.**
   - **Coordinator agent:** answers by voice about the queue, the route to the most urgent rescue, and the crews' plan.
   - **Vonage:** a resident who needs rescue can get an SMS link to share their camera, and the command post can share its map with the crews.
9. **Fallbacks.** A typed answer is classified by the LLM, or three buttons set the status. Reset restores everything between rehearsals.
10. **Autopilot.** An optional scripted run along the replay (`data/demo_timeline.json`), labelled as a simulation (#52).
11. **Live mode.** It shows the fires burning now in Spain from Deepfire, with no residents.

## What is real and what is not

| Part | In the demo |
|---|---|
| Hotspots, the fire's footprint, the lead time | **Real** satellite data from 23 July 2026 |
| Spread forecast | **Our model** from the real hotspots: simple, not validated |
| Places at risk, roads, safe points | **Real** OpenStreetMap data |
| Routes | **Real** openrouteservice routes, cached for 18:00 CEST |
| Residents | **Sample** registry of 5 (the deployed one has what `HACKFIRE_NEIGHBORS_JSON` holds) |
| The voice agents | **Real** SLNG agents and model; the resident is played by a person in the browser |
| Phone calls | **Not live:** no SIP trunk, so the agent calls the browser |
| Crew SMS | **Live through Vonage** when `HACKFIRE_CREW_PHONE` is set; the dashboard alert is the fallback |
| Autopilot outcomes | **Scripted**, and labelled as such |
| Live mode | **Real** active fires; no residents, no calls |

## Weak points, most serious first

1. **The resident agent can claim a record it never made.** In Galtea's `confused-elderly` scenario it told an 88-year-old living alone "le he registrado… ya he avisado a la coordinación" without calling `report_status`, 3 runs out of 3. A prompt rule did not fix it ([Galtea](../services/galtea.md)).
   - A phone campaign turns such a call into `no_answer`.
   - **Browser sessions now have the same safety net:** when a call that got through ends, the dashboard reports it (`POST /api/neighbors/{id}/call-ended`). Six seconds later, a resident still pending becomes `no_answer`, with the note "call again". A report that lands in those seconds wins. The agent's false claim remains, but it no longer hides a household.
2. **The model's reasoning leaked into the spoken text once** (`…</think>`). If SLNG's runtime does not strip it, the voice would read English reasoning aloud. Check on a real call before the demo.
3. **The prompt fixes of #53 and #55 are not live** until `pnpm voice:deploy`.
4. **Routes and orders use a fixed scenario time** (`HACKFIRE_SCENARIO_TIME`, 18:00 CEST), while the fire status follows the slider. With the slider elsewhere, the agent can describe the fire at one moment and give a route planned for another. This is deliberate, because routes are cached and openrouteservice's quota is spent. On stage, the call must happen with the slider near 18:00 CEST.
5. **Five residents make a thin map.**
   - The deployed registry needs 8–10 residents (PLAN.md), set by Rosa in `HACKFIRE_NEIGHBORS_JSON`.
   - New residents also need their routes cached (`pnpm data:routes`, `pnpm check:routes`), which needs an openrouteservice key with quota.
6. **The forecast over-warns by design.**
   - 56 of the 68 places are at risk at some point of the day.
   - The cone ignores wind, slope, fuel and humidity.
   - It is a convex hull that can cover places the fire never touched.
   - Say this plainly if asked.
7. **The autopilot is a script.**
   - Since autopilot v2 its orders and calls are timed from when each zone enters the forecast, and a rescue shows a real agent transcript against a Galtea resident and draws the crew route. The outcomes themselves are still scripted.
   - Evacuating and no-answer outcomes show no transcript: the agent did not record those calls in the latest Galtea runs ([Galtea](../services/galtea.md)).
   - It lags the slider by up to about 2.5 s during playback.
   - It must be off before any live call.
8. **The agents hear English sentences** (`HACKFIRE_AGENT_LOCALE=en`) and translate them while speaking. Setting `es` removes that step. Try `pnpm eval:triage` and `pnpm eval:galtea` first.
9. **Voice latency per turn has not been measured**, although PLAN.md asks for it and SLNG asks for real numbers.
10. **Railway deploys can wait for approval.** Check the deployment list before rehearsing: a merged change is not live until it is approved.

## Making the demo stronger without new features

Everything here is configuration, data or rehearsal:

- **One scripted path, rehearsed five times** (PLAN.md section 8):
  1. Play the replay with the autopilot on, to show the lead time, the cone and the strip moving.
  2. Turn the autopilot off and set the slider near 18:00 CEST.
  3. Approve La Atalaya's order.
  4. Take one resident's call live in the browser, answering "mi madre no puede andar".
  5. Show the pin turning red, the rescue queue, the crew alert and the crew route.
  6. Ask the coordinator agent for the plan.
- **Crew SMS:** already works through Vonage, which the live video also uses. Set `HACKFIRE_CREW_PHONE`
  to one team phone on Railway, and the next rescue texts it the crew route. Twilio was never set up
  and no longer appears on the service panel.
- **Deploy the agent fixes** (Roger: `pnpm voice:deploy`), then rerun `pnpm eval:galtea`.
- **Fill the registry** to 8–10 residents with the team's phones, and cache their routes.
- **Measure latency** on three browser calls and write the numbers in the pitch.
- **Record the backup video** (22:00, PLAN.md) with the autopilot run and one live call.

## A more detailed simulated workflow (only if the team lifts the freeze)

This would make the replay tell the whole story by itself. Rough effort for one person in brackets.

1. **Replay-driven calls.** The autopilot calls a zone when it first enters the forecast and its order is approved, instead of at fixed times, so the calls visibly follow the fire. (1 h)
2. **Real agent answers in the dashboard.** A call log panel plays, for each simulated call, a transcript the real resident agent produced against Galtea's simulated residents. They are real outputs of our agent, with the simulated resident clearly marked. The needs-rescue call would be the wheelchair user; the no-answer call, the wrong number. (1.5 h)
3. **Routes drawn as outcomes land.** Blue routes for evacuees and the crew route for the rescue. **Road closures done:** roads the fire reaches within the hour are drawn as a dashed red cordon, with a count in the legend, "closed to residents, crews still use them". That matches the routing: residents avoid the fire plus its next hour, crews only what has burned. (Routes drawn automatically: 1 h)
4. **Safety net for browser sessions.** **Done:** see weak point 1.
5. **Crew SMS to more than one crew.** `HACKFIRE_CREW_PHONE` becomes a list, and the crew plan decides who gets which rescue. (45 min)

Live mode stays without simulated residents. Pretending to call people near fires that are burning now would be misleading.

## After the hackathon

- **Physics in the forecast:**
  - wind from a historical weather archive (Open-Meteo needs no key) to steer the cone;
  - slope and aspect from a DEM;
  - fuel models and fuel moisture;
  - then a Rothermel-type spread (FARSITE, Wildfire Analyst), validated against the real hotspots with an IoU metric (extension 3, Devin).
- **Real telephony:** a Spanish number, the SIP trunk on SLNG, retries for no answer, and calls in the resident's language.
- **An outcome audit:** every call's transcript stored next to its recorded status, so a coordinator can check what the agent heard.
