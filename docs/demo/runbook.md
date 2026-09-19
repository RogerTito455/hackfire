# Demo runbook

How to run the three-minute demo (PLAN.md section 8) so it survives the room: the network, the voice agent or a third-party API failing. Checklist for #13; the script itself is #15.

## Before the demo (on good Wi-Fi, 10 minutes)

1. Open the **deployed** dashboard (the Railway URL) in the browser you will present from, and keep the tab open.
2. **Warm the map cache.** Pan and zoom over the demo box (Burgohondo → El Tiemblo → La Atalaya → San Martín) at the zooms you will use. A service worker keeps those OpenStreetMap tiles (`frontend/public/tile-cache-sw.js`), so the map still draws if the venue network drops. It caches tiles only, not the app: **do not reload the page offline**.
3. Press **Reset demo**. It clears every status, crew alert and evacuation order, forgets the replay moment on the server, puts the slider back at the start and closes any selected resident.
4. Check the voice agent answers (#7), and have a phone that rings for the outbound call (#8).

Everything the story needs is served from `data/`: hotspots, forecasts, zones, lead time and routes (`pnpm data:routes` caches every resident's route to every safe point). Only live mode and the voice agent talk to third parties.

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
