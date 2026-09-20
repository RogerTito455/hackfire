# Defence Q&A: the questions the jury may ask

Questions we may get after the presentation, with answers to say aloud. It complements [defense.md](defense.md), which has the hard questions, what not to say and what to check before going on stage; the presentation itself is in [presentation.md](presentation.md). As of 20 September 2026.

Answer with what the product does today and with the figures in the last section. If something has not been measured, say so plainly.

## Ground rules

**Say, before anyone asks:**

- **Real:** Deepfire's satellite hotspots of 23 July 2026, the places and roads from OpenStreetMap, the routes from openrouteservice, and the voice agents, which are real agents on SLNG.
- **Fictional:** the residents, their homes and their answers, the calls in the replay, the evacuations and the crew alerts. Nobody near the real fire was called.
- **The demo call** runs in the browser and a teammate answers it: there is no phone line yet.

**Never say:**

- That you would have saved lives or homes, or "N hours before 112".
- "Validated" about the forecast.
- "A real call" or "a real resident".
- That the fire reached the estate at 21:38: say "the first hotspot within three kilometres".
- That the crew gets a text message, unless the service panel shows Vonage configured and a crew phone set (`HACKFIRE_CREW_PHONE`). The alert always shows on the dashboard; the text goes out through Vonage only with that phone. Twilio was never set up.
- Anything about when the authorities warned: we do not have that time.

**Suggested split:** one person answers and another completes. Data and forecast, voice, and product and privacy, each with an owner.

## The problem and the idea

The idea in one sentence: turn a wildfire forecast into a conversation with every household in its path, and their answers into the coordinator's rescue plan.

**Why not just use ES-Alert?**

ES-Alert broadcasts the same message to every phone and it cannot listen. HackFire holds a conversation with each household and feeds the answers back to the coordinator. It is complementary: we draft alerts per zone and hand them over, we never send them. Public alerts belong to Civil Protection and the regional 112 services.

**Who is the user?**

The emergency coordinator, and through them the fire crews. The residents are the people we call. What changes for the coordinator is that, for the first time, they know who has left, who cannot move and who did not answer.

**Why a phone call and not an app or a push notification?**

The people most at risk are the least likely to install an app or read a notification: the elderly, people alone, people who cannot move. A call reaches a landline, speaks their language and hears the answer.

**What if the phone network fails during a fire?**

We call on the forecast, hours ahead, while the towers still work. And "no answer" is a signal too: it tells the coordinator where to send a patrol. In the late-July fires, 16 municipalities lost mobile or landline coverage (The Objective, 29 July; not broken down by fire).

**What happened on 23 July?**

The Burgohondo fire, in Ávila, ran three kilometres in forty minutes and reached the La Atalaya estate in El Tiemblo. About 1,300 people were evacuated from it and five homes were destroyed (Tribuna de Ávila and Ávilared, 23 July).

**What is your workflow, step by step?**

1. Deepfire's satellite hotspots and a forecast of where the fire is heading.
2. The forecast is crossed with towns, care homes, schools and roads: each place gets a time to impact.
3. A person approves the order for each zone; only then are its residents called.
4. The voice agent calls, gives the route and asks whether they can leave on their own.
5. Each resident ends as evacuating, no answer or needs rescue; rescues are ranked with the crew's route.

*Team note:* if the question is broad, answer in two sentences and offer to show the dashboard; do not recite the five steps unless asked.

## Data and forecast

What to keep clear: the fire and the places are real, the forecast is our own simple model and it is not validated outside this fire. The accuracy figures below come from an analysis of our own on 20 September, done on this same fire (the scripts are not in the repository).

**What is real and what is simulated?**

The fire data is real: 7,068 Deepfire satellite hotspots from 22 to 24 July 2026. Places and roads come from OpenStreetMap and routes from openrouteservice. The residents, their homes and their answers are fictional, and so are the calls, evacuations and crew alerts in the replay.

**How does your forecast work?**

From the last three hours of hotspots we estimate the front's heading and speed, and project the current footprint forward hour by hour, up to six hours, as a cone. The speed is clamped between one and six kilometres an hour, and the shape is deliberately biased to over-warn. It uses no wind, terrain, fuel or humidity yet.

**How accurate is it?**

Honestly: it is not validated on other fires. On this one, it covers about 77% of the ground the fire newly moved into, against 52% for the same cone with a random heading and 28% for a fire that does not grow. At the level of places, it flags 55% of those the fire reaches within six hours and 66% of its warnings are not confirmed, because it over-warns on purpose. The timing is off by about two hours either way. Our constants were tuned on this fire, so these numbers are optimistic.

**Why not use Deepfire's own simulation?**

The documented simulation starts from at most 168 hours back and has no start-time field, so it cannot replay 23 July. We checked all 3,111 runs it keeps and none covers that day. In live mode we do use Deepfire's own ELMFIRE simulations for the fires burning now.

**What is the lead time, and how is it computed?**

About six hours, from satellite data alone. The forecast flagged La Atalaya at 15:30 local time; the first hotspot within three kilometres of it came at 21:38. It is a range, five to eight hours, depending on the distance you take as arrival, because a single satellite pixel decides it. It says nothing about when anyone was warned.

**Isn't six hours long for a fire that ran three kilometres in forty minutes?**

The lead time is the gap between our flag and the first hotspot near the estate, not the speed of the front. And it is one event: if you count arrival at five kilometres it is five hours, and the fire only came within one kilometre of the estate the next day.

**Does it work on other fires?**

Live mode works on any fire burning in Spain that has a Deepfire simulation: it shows the places at risk with their time to impact, a draft alert per place and the roads to close. The replay runs from a scenario file. What we have not measured is the accuracy of the forecast on other fires.

**Why is the cone a convex hull?**

It is the simplest shape that covers scattered hotspots, and it errs on the side of warning. The cost is that it can cover places the fire never touched.

*Team note:* if asked about "the accuracy", always give the three figures (coverage, false alarms, timing) and add "on one fire".

## The voice agent

This is where you will be pressed hardest, and the honest answer is this: the agent decides the clear cases well, but it has been measured recording a rescue wrongly some of the time. The figures come from our own evaluation on 20 September, with 156 simulated conversations and the resident prompt of that day, which `main` has not changed since; the simulated residents followed fixed scripts, not adaptive ones. They can change when a new prompt is deployed.

**How reliable is the agent?**

We tested it before anyone asked. On unambiguous answers it recorded an outcome 96% of the time and got clear evacuations right every time. But in our tests about 18% of clear rescue cases were recorded as "evacuating", so we do not trust it alone. A person approves every order, every answer lands on the coordinator's map, a call that ends unrecorded becomes "no answer, call again", and a typed answer or three buttons replace a failed call. The agent informs and asks; people decide.

**What if the agent says it recorded something and did not?**

Galtea's simulated residents found exactly that on an earlier version of the prompt: an 88-year-old alone was told "I have recorded that you need help" and nothing was recorded. The prompt alone did not fix it, so the fix is in the backend: when a browser call ends with nothing recorded, the resident is flagged for a follow-up call after six seconds. In our latest test it happened in about 1% of conversations.

**What if the resident hangs up early?**

The prompt says to record as soon as it is clear whether they can leave, but the model often waits until after the three questions. If they hang up before, the pin stays pending, and the same safety net turns it into "no answer" so the coordinator knows to call again. We know it is a weakness.

**How fast is it?**

The model's answer through SLNG takes about half a second, with 90% under 0.9 seconds. We have not measured the whole turn, with speech recognition and synthesis, on real calls yet. Four of about 740 model calls stalled for over 90 seconds, so a stall is possible.

**What language does it speak, and which model?**

Castilian Spanish, addressing people as *usted*, with a Deepgram Aura voice. The model is NVIDIA Nemotron Super 3 (120 billion parameters), served by SLNG at low temperature so the same answer gets the same triage. For Spanish in an EU region, SLNG's agents accept only the two Nemotron models. Catalan is listed by SLNG but the demo residents speak Spanish.

**Does it pretend to be a person or the 112?**

No. It says it is an automatic assistant working for the emergency coordination and never claims to be the 112 or an official service.

**How does it treat frightened, elderly or difficult residents?**

Short calm sentences, one question at a time, and it repeats what matters more slowly. We tested six simulated residents: a prank caller, a confused 88-year-old, a panicked mother, a man who refuses to leave, a wheelchair user and a wrong number. Several of those found real failures, which is why the prompt has been changed more than once.

**Are the calls real?**

Not yet: we have no phone line. The call runs in the browser and a teammate plays the resident; the agent and its model are real. With a SIP trunk, the "Call residents" button phones every pending resident of an approved zone.

**Could the model read its own reasoning aloud?**

It happened once in an earlier test, ending in a stray tag. It did not happen in our 156 latest conversations, but we still have to check it on a real call.

*Team note:* do not improvise the resident's answers in the demo. The scripted line, "Yo puedo salir, pero mi madre no puede andar", came out right all three times; phrases such as "humo por todas partes" or "nos quedamos a defender la casa" failed. If the agent says something odd, use the typed answer as a backup.

## Product, operation and privacy

The defence here is that a person is in the loop and that personal data does not leave the server. What is not settled (the legal basis in a real pilot, a retention policy, scale) is said as pending, not improvised.

**Who decides? Is there a human in the loop?**

Yes, at every step that matters. The system proposes an order for each zone: the nearest safe town the forecast does not reach, or staying indoors. The coordinator approves it or changes it, and nobody is called before that. The agent transmits the order; it does not invent its own or give advice.

**Where do the phone numbers come from?**

From a voluntary registry that the municipality or the emergency services already hold, such as the municipal register or the vulnerable-person lists in civil protection plans, on a legal basis of vital or public interest. The numbers never leave the backend: the API excludes them by design. In the demo the residents are fictional.

**What about privacy and GDPR?**

We keep the minimum: the outcome of each call (status, people, mobility, a few words of what they saw) and an audit log of every order, call and outcome. What we have not done is a data protection impact assessment or a retention policy; for a pilot we would define both with the municipality. Audio is handled by the voice provider, SLNG.

**Won't this annoy people with false alarms?**

It over-warns on purpose, because a missed household costs far more than an unnecessary call. That is why only zones in the forecast are called, a person approves each order, and "no answer" leads to a patrol rather than a rescue. The trade-off is measured: about two in three warnings are not confirmed within six hours.

**What does the crew get?**

Every new rescue creates an alert with the address, people, mobility and a link to the route from the El Tiemblo fire station. A crew plan assigns crews to rescues in order and says whether each is in time. The alert always shows on the dashboard, and it goes out as a text through Vonage when a crew phone is set; check the service panel before saying it does. A resident who needs rescue can also share live video through Vonage, and the command post can share its map with the crews.

**What if a road is closed or the fire cuts it?**

Roads the fire has reached are treated as closed, and the coordinator can close any other with a tap. Every route asked after that goes around it, and the residents who were using it are named so they can be called again.

**What happens if a provider fails during the demo?**

The demo is built to survive it. Hotspots, forecast, places and routes are cached files, Deepfire's 503s are served stale, and a road closure works without openrouteservice. If the voice fails, a typed answer classified by the same rules, or three buttons, replace the call. There is also a backup video.

**Does it scale?**

Calls run in parallel on a SIP trunk, so capacity is a contract, not code. Today's limits are honest ones: no phone line yet, the state lives in memory so a redeploy resets it, and openrouteservice's free quota, which is why the demo's routes are cached.

**Can what happened be audited?**

Yes. Every order, campaign, call and outcome is in an activity log with its source, and the whole run can be downloaded as JSON. The status of each external service is on the dashboard too.

*Team note:* if asked about GDPR, do not promise what is not done; "we would define it with the municipality in the pilot" is a valid answer.

## Technology and sponsors

Say what each service does in the product and what is really done; what is only an idea (Devin) is presented as roadmap, not as an achievement.

**What did you build this weekend?**

The whole chain: satellite hotspots on a map with a time slider; a forecast and the places at risk with their time to impact; the lead time; evacuation orders per zone; routes that avoid the fire; two voice agents, one for the residents and one for the coordinator; triage into three states; a rescue queue and a crew plan; road closures; live video with Vonage; a live mode on real fires; the interface in English and Spanish; and an evaluation suite.

**What is your stack?**

FastAPI for the backend, React with MapLibre for the dashboard, one Railway service that serves both, OpenStreetMap for places, openrouteservice for routes, Deepfire for fire data and SLNG for the voice agents and the model behind them.

**Why SLNG?**

It gives us the voice, the speech recognition and the language model in one place, with an agent builder that can call our own tools over HTTPS. The agent reaches our backend through five tools: fire status, evacuation route, report status, rescue queue and rescue route.

**How did you use Deepfire?**

It is the source of the fire: the satellite hotspots we replay, the active fires in live mode and, there, its own ELMFIRE spread simulations. We cache everything for the demo because Deepfire runs on shared capacity and can return 503 under load.

**And Vonage?**

A resident who needs rescue can get a link, open their camera in the browser, and the coordinator sees them on the dashboard with live captions. The command post can also share its map and voice with the crews. It was an extension after the core worked.

**What did Norma and Galtea do for you?**

Galtea simulates residents, some of them adversarial, and call-tests the agent's triage: it found real failures we then worked on. Norma's portal scan reported 148 findings. We fixed the ones that were real defects, including the XML parser of the DGT feed, the missing Content-Security-Policy, the Reset button that did nothing when the backend was down and the requests that could hang forever, and we wrote down, at the line itself, why we left the rest: mostly rules that match something else, such as a terminal command that prints. The full account, with the counts, is in [DEFENCE.md](../../DEFENCE.md). The editor could not link the repository to Norma's organisation, so we measured each change file by file with its live check, and nothing is recorded in its audit trail.

**And Devin?**

It is on the roadmap, not built. The idea is that after every fire it replays the forecast against the real hotspots, measures the error, proposes a better model, and nothing ships unless it beats today's model on fires it has never seen.

**Did you use AI to write the code?**

Yes, with AI coding assistants, and we controlled the quality: over 250 backend tests, the Norma scans, and separate evaluations of the forecast and of the voice agent whose weaknesses we report openly.

**How was the presentation video made?**

It is drawn in code with Remotion from the same data the dashboard uses, with ElevenLabs voices for the narration and the simulated call. The screen says the real agent speaks Spanish.

*Team note:* whoever gets the question about AI answers it naturally; do not dodge it. It is consistent with everything else: we measured and published what fails.

## Impact, competition and next steps

The key here is to separate what exists from what would be a pilot, and not to invent figures for cost or impact: none has been calculated.

**How is this different from Watch Duty or focs.cat?**

Both are pull-based, one-way and need a smartphone with data. Neither gives a resident a personal instruction, neither hears an answer, and neither tells the coordinator who cannot move. Watch Duty verifies its alerts with human reporters and only notifies when life or property is threatened; we borrowed that threshold, its per-fire timeline with sources, zone-based targeting and a human approving before anything goes out at scale.

**Who would pay for this?**

We have not costed it, and we prefer not to invent a number. The natural customers are civil protection and emergency services, or the municipalities that run a voluntary registry; the main costs would be voice minutes and the phone line.

**What would a pilot look like?**

One municipality with a voluntary registry, a real phone line through a SIP trunk, a person at the control post who can take over a call the agent should not carry alone, and the forecast measured against every fire that happens. Only then would the numbers mean something.

**What is next?**

1. Real phone lines and a handover of the call to a person at the control post.
2. A forecast with physics: wind from a weather archive, slope from a terrain model, fuel and moisture, validated against many fires and not just one.
3. The DGT's official road incidents, already shown in live mode, brought into every route; more regions and more languages.
4. Living inside 112 and the crews' own workflow.
5. Devin retraining the forecast against every new fire, and the outcome of every call feeding new tests for the agent.

**What about volunteers?**

Out of scope on purpose. Sending untrained people towards a wildfire is a serious risk; if it is ever built it must be logistics support away from the front and always under the coordinator's orders.

**Could this work for other hazards?**

The chain is not specific to fire: a forecast, the people in its path, a conversation and a triage. But we only built and tested it for wildfire, and the forecast is the fire-specific part.

**What would you do with more time?**

Validate the forecast on other fires with success criteria written before we look, fix the way the agent records a rescue, and get a real phone line. Those three turn a demonstration into something a coordinator could try.

*Team note:* "next" always starts with validation and the phone line: they are what makes you most credible in front of a technical jury.

## Tricky or uncomfortable questions

These are the ones the jury asks to see how you react. The formula that works: acknowledge the limit, give the measured figure and say what you would do to close it. Never defensive.

**Would this have saved lives that day?**

We cannot rerun that day, and nobody can measure what a different warning would have changed, so we make no claim. What HackFire changes is what the coordinator knows, and when: every household answers, and each answer reaches the map within two seconds.

**Did the authorities fail?**

We do not know when they warned or what they did, and we make no claim about it. Our lead time is computed from satellite data only, and people lost their homes in that fire.

**Is your forecast validated?**

No, and we say so. It is a transparent model, tuned on this one fire. In this fire it beats a fire that does not grow and a random heading, but we have not tested it on others. The next step is to write the success criteria before looking, and run it on fires the model has never seen.

**Your agent could tell someone with a disability that they are fine. What then?**

That risk is the reason for the design. We measured it: in our tests about one in five clear rescue cases was recorded as an evacuation. So an order needs a person's approval, every answer is on the coordinator's map, a call without a recorded outcome becomes "no answer, call again", and the coordinator can override with the typed answer or the buttons. We treat the agent as an assistant to people, not a replacement, and the first thing we would fix is how it records a rescue.

**Is that a real call? A real resident?**

No. The residents are fictional and the call runs in the browser with a teammate answering. The agent and its model are real, and so is the fire data.

**Your six hours: can I trust that number?**

It is a description of one event, not a statistic. The forecast flagged La Atalaya six hours before the first hotspot within three kilometres. With five kilometres it is five hours, and it depends on the satellite pixel. We give it as a range, five to eight hours, and we say how it is computed.

**Why is your forecast so cautious? It flags places that never burn.**

Because a missed household costs more than an unnecessary call. Two in three warnings are not confirmed within six hours; in exchange it finds more than half of the places the fire really reaches. The right balance depends on how much worse a miss is than a false alarm, and that is a decision for the emergency services, not for us.

**What if the agent is wrong about a resident who refuses to leave?**

The rule in its prompt is that a refusal is recorded as a rescue, so the coordinator knows. We found that it does not always follow it, which is one of the failures we would fix first. The order and the decision to send a crew remain with people.

**Do you store the calls? Are they recorded?**

Our backend stores the outcome of each call and an audit log, not audio. The audio and the call reports are handled by SLNG. What is kept and for how long is something we would settle with the municipality in a pilot.

**Is this just a demo with fake data?**

The fire, the places, the routes and the agents are real; the residents and their answers are fictional, and we say so on screen. We built a live mode for that reason: it runs on the fires burning now in Spain, without residents or calls, so the forecast and the places at risk are not a replay.

**Could it be misused, for example to call people without an order?**

Not without a person: a zone's residents are called only after its order is approved, and the campaign, calls and outcomes are all in the audit log. In the demo, the button that phones people is off because there is no phone line.

*Team note:* if you are cornered, the way out is: "That is a fair limit, we measured it, and this is what we would do next." Repeating it calmly is worth more than defending.

## Figures, with their source

The press and data figures are checked in the repository; the accuracy figures come from an analysis of our own on 20 September, valid only for this fire and this prompt, whose scripts are not in the repository.

| Figure | Value | Where it comes from |
| --- | --- | --- |
| Replay hotspots | 7,068, from 22 to 24 July 2026, seven sensors (62% are MTG, with a 3 km pixel) | `data/hotspots_2026-07-22_24.geojson`, Deepfire |
| The fire | 3 km in 40 minutes; about 1,300 people evacuated from La Atalaya (1,200 to 1,300); 5 homes destroyed | Tribuna de Ávila and Ávilared, 23 July; [press figures](../findings/2026-09-19-press-figures.md) |
| Cost of the day | About 38,000 ha (37,818, provisional); 229 homes inside the burned area | Junta de Castilla y León via Ávilared, 21 August; Idealista's estimate via Ávilared, 31 July |
| Coverage lost in the late-July fires | 16 municipalities (not broken down by fire) | The Objective, 29 July |
| La Atalaya's lead time | About 6 h (5 to 8 h by distance); flagged at 15:30, first hotspot within 3 km at 21:38 | [lead time](../findings/2026-09-19-lead-time.md) |
| Places analysed | 68; 56 at risk at some moment of the day | [spread cone model](../findings/2026-09-19-spread-cone-model.md) |
| Deepfire simulations | 3,111 runs; none covers 23 July | [no historical simulation](../findings/2026-09-19-deepfire-no-historical-simulation.md) |
| Forecast: new ground covered | 77%, against 52% (random heading), 62% (disk of the same area) and 28% (no growth) | Our own analysis, 20 September; one fire, constants tuned on it |
| Forecast: places reached | Flags 55% within 6 h (at 3 km); 66% of its warnings are not confirmed; timing off by about 2 h | Same analysis |
| Forecast: heading | Median error of 82°; 42% within 45° (chance gives 25%) | Same analysis |
| Agent: recording | 96% of the conversations with a clear answer record an outcome; clear evacuations, 100%; wrong number, 92% | Our own evaluation, 156 simulated conversations, 20 September |
| Agent: serious error | 18% (95% CI 6 to 33%) of clear rescues are recorded as "evacuating" | Same evaluation |
| Agent: when it records | Only 3.5% record before the three questions | Same evaluation |
| Agent: speed | Model: median 0.5 s, 90% under 0.9 s (without speech recognition or synthesis) | Same evaluation, 741 model calls |
| Code quality | Over 250 backend tests; Norma: 148 findings in the portal scan, with the fixes and the decisions not to fix listed | `pnpm check`; [DEFENCE.md](../../DEFENCE.md) |

## What to say when you do not know

Inventing a figure is worse than admitting you do not have it. These phrases almost always work, in this order: acknowledge, say what you do know, and propose how you would measure it.

- **"We haven't measured that."** Then say what you did measure that is closest, and how you would test the rest.
- **"That is outside what we built this weekend."** Then name where it sits on the roadmap.
- **"I'd rather not guess a number."** Then give the range you do have, with its limits.
- **"My teammate can answer that better."** Then hand over by name: data and forecast, voice, or product and privacy.
- **"That is a fair limit."** Then: what we measured, and what we would do next.

**Three true things you can always return to:**

1. A person approves every order and sees every answer: the agent informs, people decide.
2. What is real and what is fictional is said on screen and in the talk.
3. Everything that failed in our tests is measured, and we have told you.
