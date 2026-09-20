# Presentation script: explaining HackFire, live

Three minutes on stage (PLAN.md section 8): what the project is, why it exists, and the product working. It supersedes the timings of [the pitch draft](pitch.md), which stays as the source of the checked figures and the questions. Wording is a draft for whoever presents: change it, but keep the numbers and the [things not to say](defense.md#what-not-to-say).

The presentation video is submitted on its own and explains itself. This talk does not describe it or depend on it; it is only the last resort if the demo cannot run (see the failure table).

## People

- **Presenter**: talks and drives the dashboard.
- **Resident**: a teammate who answers the call in Spanish, off camera or beside the presenter, with the lines below.
- Optionally a **third person** with the runbook open, ready to press the fallbacks.

## Before going on stage

The full list is the [runbook](runbook.md); these are the ones this script depends on.

1. Railway has **approved the last deploy**, and `pnpm voice:deploy` has run, so the prompt fixes are live.
2. **Reset demo**, then drag the replay slider to about **15:00 CEST** (before La Atalaya's flag at 15:30). **Simulate the calls stays off**: it would be overwritten by a live call.
3. The resident registry has the residents the call needs, and `pnpm check:routes <url>` passes against the deployment.
4. Microphone allowed in the browser. One test call done, and the agent does **not** read its reasoning (`</think>`) aloud.
5. Never deploy during the demo: the state lives in memory.

## Run sheet

| Clock | On screen | Say / do |
|---|---|---|
| **0:00–0:50** | Dashboard, replay, slider at ~15:00 | Section A: who we are, the problem, the idea |
| **0:50–1:18** | Same | Section B. Press *Play replay*; pause when the lead-time card appears |
| **1:18–1:27** | *Evacuation orders* | Section C. Move the slider to about **18:00 CEST**, then press *Approve order* |
| **1:27–2:12** | Click a La Atalaya resident → *Call this resident* → *Call … (answer here)* | Section D. The resident answers in Spanish |
| **2:12–2:38** | Rescue queue, alert, *Show crew route*, then *Ask the coordinator agent* | Section E |
| **2:38–2:49** | Dashboard | Section F |
| **2:49–3:00** | Dashboard, pin red | Section G |

The slots include the clicks. The spoken text is about 150 words a minute and has not been rehearsed against a stopwatch yet: time it, and cut from F first.

The call must happen with the slider near 18:00 CEST: routes and orders use a fixed scenario time, while the fire status follows the slider ([workflow review](workflow-review.md), weak point 4).

## What to say

**A. Who we are, the problem, the idea (0:00–0:50)**

> Good afternoon. We're [names], and this is HackFire.
>
> On the 23rd of July, the Burgohondo wildfire in Ávila ran three kilometres in forty minutes and reached the La Atalaya estate. The warning was an ES-Alert: one message to every phone. It can't tell the coordinator who has left, who can't move, or who never got it.
>
> HackFire listens back. It forecasts where a fire is heading, then a voice agent calls the households in its path, gives each one a way out, and asks whether they can leave on their own. Every answer lands on the coordinator's map, so firefighters go only where they are truly needed.
>
> The fire data and the agent are real; the households are fictional.

**B. The forecast (0:50–1:18)**

> This is that day, from Deepfire's satellite hotspots. *(Play.)*
>
> *(Pause on the lead-time card.)* At 15:30, using only what the satellites had seen up to then, the forecast puts La Atalaya in the fire's path. The first hotspot within three kilometres came at 21:38. That is about six hours of lead time, from satellite data alone: five to eight, depending on where you measure from. It says nothing about when anyone was warned.

**C. The order (1:18–1:27)**

> A person approves the order: leave for *(the destination on screen)*, the nearest safe town the forecast does not reach. Nobody is called before that.

Read the destination from the panel instead of from this page: it depends on the registry and the scenario time.

**D. The call (1:27–2:12)**

> Now the agent calls a resident. It speaks Spanish, like the residents do, and a teammate plays her.

The agent opens with the order and the route, then asks whether she can leave on her own, how many they are, and what she sees. The resident says, in Spanish:

1. "Yo puedo salir, pero mi madre no puede andar." *(I can leave, but my mother can't walk.)*
2. "Somos dos." *(There are two of us.)*
3. "Veo mucho humo, pero no veo llamas." *(I see a lot of smoke, but no flames.)*

Say nothing while the agent talks. When it hangs up:

> She can leave; her mother can't. The agent understood that from what she said, not from a keyword. The pin turned red within two seconds.

**E. The rescue (2:12–2:38)**

> Every resident who can leave is on their way. The ones who can't land here, ranked by how soon the fire reaches them, with the crew's route. *(Press* Show crew route.*)* It goes around what has burned, and the coordinator can close any other road with a tap.
>
> The coordinator can also just ask. *(Press* Ask the coordinator agent*; say:* "¿Qué rescates tengo y en qué orden?" *— which rescues do I have, and in what order.)*

The alert reads "Dashboard only, SMS not set up": do not say the crew gets a text.

**F. What is next (2:38–2:49)**

> Next: real phone lines — today the call runs in the browser — and a handover to a person at the control post.

**G. Close (2:49–3:00)**

> HackFire doesn't replace ES-Alert. It listens back. Every resident who leaves on their own is a rescue the firefighters don't have to make.

## If something goes wrong

| Failure | Do this | Cost |
|---|---|---|
| The agent does not answer, or the room is too loud | Pin → *Typed answer (backup)*, type "Mi madre no puede andar", *Classify and record* ([runbook](runbook.md)). Say: "The call is the input; this is the same triage from typed text." | +0:15 |
| No LLM either | The *Needs rescue* button under the text box | +0:05 |
| Running late | Cut F, then skip the coordinator's voice question in E | −0:20 |
| Laptop or network dies | Play the submitted presentation video from a second device, and say only the last sentence of G when it ends | The demo becomes the video |
| The call starts but the agent claims it "recorded" something and the pin does not move | Wait six seconds: a call that ends unrecorded becomes *no answer* ([Galtea](../services/galtea.md)). Say so, and use the typed answer | +0:20 |

## Say and do not say

- Say **"the first hotspot within three kilometres"**, never that the fire reached the estate at 21:38.
- Say the household is **fictional**, the agent is **real**, and the call runs **in the browser**. Never "a real resident" or "real calls".
- Say the forecast is **our model from satellite data**, not "validated" ([defense](defense.md)).
- The only headline number is the lead time. No "would have saved", no "N hours before 112".
- Do not claim SMS to the crew or a phone ringing in the room: there is no phone line and Twilio is not set up.

## Questions

[defense.md](defense.md) has the hard ones and their honest answers. The three that come first: *why not ES-Alert* (it broadcasts and does not listen), *what if there is no coverage* (we call on the forecast, hours ahead, and "no answer" is a signal), and *how good is the forecast* (a cone from the front's velocity, biased to over-warn, not validated on another fire).
