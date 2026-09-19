# Demo runbook

How to run the three-minute demo (PLAN.md section 8) so it survives the room: the network, the voice agent or a third-party API failing. Checklist for #13; the script itself is #15.

## Before the demo (on good Wi-Fi, 10 minutes)

1. Open the **deployed** dashboard (the Railway URL) in the browser you will present from, and keep the tab open.
2. **Warm the map cache.** Pan and zoom over the demo box (Burgohondo → El Tiemblo → La Atalaya → San Martín) at the zooms you will use. A service worker keeps those OpenStreetMap tiles (`frontend/public/tile-cache-sw.js`), so the map still draws if the venue network drops. It caches tiles only, not the app: **do not reload the page offline**.
3. Press **Reset demo**. It clears every status, crew alert and evacuation order, forgets the replay moment on the server, puts the slider back at the start and closes any selected resident.
4. Check the voice agent answers (#7). Without a phone line (no SIP trunk, `HACKFIRE_PHONE_CALLS` off), the call runs in the browser: approve La Atalaya's order, click a resident's pin → **Call this resident → Call … (answer here)**, allow the microphone, and someone answers as the resident. The pin changes within two seconds of the agent recording the answer. With a trunk, **Call residents** on the approved order rings every resident's phone instead.

Everything the story needs is served from `data/`: hotspots, forecasts, zones, lead time and routes (`pnpm data:routes` caches every resident's route to every safe point). Only live mode and the voice agent talk to third parties.

## Simulating the calls along the replay (off by default)

The replay alone leaves the status strip at "Not called yet" for every resident. To show the coordinator's workflow while the slider moves, switch on **Simulate the calls** (*Simular las llamadas*) under the replay scrubber. The strip then shows a line saying it is a simulation with the demo residents, not what happened on 23 July.

- **What it does.** As the slider moves, the backend plays the fixed script in `data/demo_timeline.json` (`backend/app/autopilot.py`): after La Atalaya is first flagged (15:30 CEST) the zones' proposed orders are approved, residents start evacuating, one does not answer, one needs rescue (rescue queue and crew alert on the dashboard) and the one who did not answer is reached on a retry. Scrubbing back undoes it. Residents are named by their position in the registry, so the same script works with the sample and the deployed registry.
- **It never phones or texts anyone.** It writes the dashboard's state directly, never through `report_status`, so no crew SMS is sent. While it is on, **Call residents** and the rescue video request answer 409, because both reach real phones.
- **Turning it off** puts back the residents, orders and alerts as they were before it was switched on. **Reset demo** also turns it off and clears everything.
- **Turn it off before any live call.** Anything the voice agent records while it is on is overwritten on the next slider move and thrown away when it is switched off.
- From a terminal: `curl -X POST <url>/api/autopilot -H 'Content-Type: application/json' -d '{"enabled": false}'`; `GET <url>/api/autopilot` says whether it is on.

## If something fails on stage

| Failure | What to do |
|---|---|
| The voice agent does not answer, or the room is too loud | Click the resident's pin → **Typed answer (backup)**. Type what the resident says ("Mi madre no puede andar") and press *Classify and record*: the LLM triages it with the voice agent's rules and the pin, rescue queue and crew alert react as after a call. Needs `SLNG_API_KEY` on the backend, Railway included |
| No LLM either | The three buttons under the text box (*Evacuating*, *No answer*, *Needs rescue*) set the status directly, through the same `report_status` path |
| Deepfire is down (live mode) | Live mode shows "Deepfire is unavailable right now. The replay still works." Stay in replay |
| openrouteservice is down | Demo routes are cached; a route never planned before answers 503 "Routing is unavailable right now" |
| Venue network drops | The open tab keeps working with cached tiles; the API needs the network (Railway). Last resort: the 60-second backup video (#15) |
| Something looks wrong mid-rehearsal | **Reset demo** and start again |

## Still open in #13

- Push-to-talk instead of open listening, and pre-recorded resident audio: voice track (#7, Roger).
- Feature freeze Saturday 21:00.
