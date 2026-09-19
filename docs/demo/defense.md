# Defending HackFire in front of the jury

A companion to the [pitch script](pitch.md). The pitch has the three minutes and the short answers; this page has the hard questions, the honest answers, and what to check before going on stage. Every answer here matches what the code does tonight, 19 September 2026. If the product changes, change the answer.

## The claim, in one breath

HackFire turns a wildfire forecast into a conversation with every household in its path, and turns their answers into the coordinator's rescue plan. It does not replace ES-Alert; it listens back.

## What is real and what is not

Say this before anyone asks. The dashboard and the landing page say it too.

- **Real:**
  - the fire data: Deepfire's 7,068 satellite hotspots of 22–24 July 2026;
  - in live mode, the fires burning now in Spain and Deepfire's ELMFIRE simulations;
  - the places and roads (OpenStreetMap), the routes (openrouteservice), and the DGT road incidents when that lands;
  - the voice agents: real AI agents on SLNG, with Nemotron Super and a Deepgram voice.
- **Fictional:**
  - the residents, their homes and their answers;
  - the calls and evacuations in the replay;
  - the crew alerts.

  Nobody near the real fire was called.

## Hard questions

| Question | Honest answer |
|---|---|
| **Your AI calls vulnerable people. What if it gets it wrong?** | We tested it before anyone asked. Galtea's simulated residents (a prank caller, a confused 88-year-old, a panicked parent, a man who refuses to leave, a wheelchair user, a wrong number) found real failures. In the worst one, the agent told the confused elderly woman "I've recorded you" without recording anything. We added a safety net: a call that ends unrecorded becomes "no answer", so the coordinator calls again. Every order is approved by a person, and every answer lands on the coordinator's map. The agent informs and asks; people decide ([Galtea](../services/galtea.md)) |
| **How accurate is the forecast?** | Two answers. The replay uses our own transparent cone from the front's velocity, because Deepfire's physics simulation cannot start in the past: we checked all 3,111 runs it keeps, and none covers 23 July. Live mode uses Deepfire's own ELMFIRE simulations (terrain, fuel, weather). The cone is deliberately biased to over-warn and has not been validated on another fire. Say so |
| **Is "about 6 hours" real?** | It is computed from satellite data only: the forecast flagged La Atalaya at 15:30 and the first hotspot within 3 km came at 21:38. It is a range, 5 to 8 hours depending on the distance, because one satellite pixel decides the arrival and the model was tuned on this fire. It says nothing about when anyone was warned ([finding](../findings/2026-09-19-lead-time.md)) |
| **Does it work on a fire other than your demo?** | Yes, in two ways. Live mode works on any active fire in Spain with a Deepfire simulation: it shows the places at risk with their time to impact, a draft alert per place (not sent) and the roads to close ([real life](real-life.md)). And the whole replay workflow runs from a scenario file, proved end to end on a synthetic fire in the tests ([new scenario](../setup/new-scenario.md)) |
| **Why a phone call and not an app?** | The people most at risk are the least likely to install an app or read a push notification: the elderly, people alone, people who cannot move. A call reaches a landline, speaks their language, and hears the answer |
| **What if the network is down?** | Calls start on the forecast, hours ahead, while the towers still work. "No answer" is itself a signal: it tells the coordinator where to send a patrol |
| **Where do the phone numbers come from? Privacy?** | From a registry the emergency services or the municipality hold, such as the municipal register or the vulnerable-person registries in civil protection plans, on a legal basis of vital or public interest. The numbers never leave the backend: the API excludes them by design |
| **Why not send the alerts yourselves?** | Public alerts (ES-Alert, zone SMS) belong to Civil Protection and the regional 112 services. HackFire drafts them per zone and hands them over; it never sends them. The CAP 1.2 export, if it lands tonight, is the standard format for that hand-over |
| **Does it scale?** | Calls run in parallel on a SIP trunk; capacity is a contract, not code. The triage, queue and routes are cheap. Today's limits are honest ones: no phone line yet, the state lives in memory, and openrouteservice's free quota (the demo's routes are cached) |
| **What happens when a provider fails?** | The demo is built to survive it. Hotspots, the forecast, the places and the routes are cached files. Deepfire is served stale when it answers 503. A road closure keeps working without openrouteservice. The typed answer and three buttons replace a failed call |
| **What did you build in the weekend?** | The whole chain: forecast, places at risk and lead time; orders; routes that avoid the fire; two voice agents (resident and coordinator); triage; rescue queue; crew plan; road closures; live video (Vonage); live operations on real fires; English and Spanish end to end; an evaluation suite (Galtea) |
| **What did the authorities do that day?** | We don't know their timing, and we make no claim about it |

## What not to say

- Anything that "would have saved" people or homes, or "N hours before 112".
- "The fire reached the estate" at 21:38. Say "the first hotspot within 3 km".
- "Real calls" or "a real resident". The calls in the demo happen in the browser, with a teammate playing the resident.
- "Validated" about the replay's forecast.

## Is the demo solid? Before going on stage

**Strong:** real fire data, a full chain from forecast to rescue queue, two languages, a working live mode on real fires, a clear honesty about what is simulated, and fallbacks for every provider.

**Risky, and what to do:**

1. **Late changes.** A lot changed after the freeze. Rehearse the exact path at least five times on the deployed URL ([runbook](runbook.md)), and check that Railway approved the last deploy.
2. **The voice agent.** The prompt fixes found by Galtea take effect only after `pnpm voice:deploy`. Check on a real browser call that the reasoning (`</think>`) is not read aloud. If the call misbehaves, use the typed answer.
3. **Two lines in the pitch script do not match the demo yet:**
   - "A phone rings in the room": there is no phone line. The agent calls the laptop, and a teammate answers in the browser.
   - "With Twilio, an SMS reaches the crew phone": Twilio is not set up. The crew alert shows on the dashboard.

   Change them unless a SIP trunk and SMS are configured before the demo.
4. **State in memory.** A redeploy resets it. Press Reset before the demo and never deploy during it.
5. **The autopilot.** Turn it off before any live call.
6. **Latency.** Measure three browser calls and put the numbers in the pitch (#14). SLNG will ask.

## Numbers you can use, and their source

| Number | Source |
|---|---|
| About 6 hours of lead time, 5 to 8 by distance | [lead time](../findings/2026-09-19-lead-time.md) |
| 7,068 satellite hotspots, 22–24 July | `data/`, [Deepfire](../services/deepfire.md) |
| 3 km in 40 minutes, about 1,300 evacuated from La Atalaya, 5 homes | [press figures](../findings/2026-09-19-press-figures.md) |
| Galtea scenarios: which passed and which failed | [Galtea](../services/galtea.md) |
| Live mode: fires with an ELMFIRE run, and places, drafts and roads for one fire | Count them on the day: they change with the fires |
