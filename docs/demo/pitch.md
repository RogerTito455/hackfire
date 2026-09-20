# Pitch script (draft)

> **To rehearse the talk with the video, use [presentation.md](presentation.md)**: its timings, cues and fallbacks replace this page's. This one stays for the checked figures, the comparison table and the questions.

Three minutes, following PLAN.md section 8, updated to what the product does now. **Draft for the team:** the presenter is still to be chosen (#15, before Saturday 21:00), and the wording should be theirs. Every figure here is checked ([press figures](../findings/2026-09-19-press-figures.md), [lead time](../findings/2026-09-19-lead-time.md)).

**Tone.** A real fire, two months ago; people lost their homes. No "we would have saved…", no "N hours before 112", no comparison with what the authorities did. The one headline number is the lead time, and we say how it is computed.

## 1. The problem (0:00–0:20)

> On the 23rd of July, the Burgohondo fire ran three kilometres in forty minutes and reached the La Atalaya estate, in El Tiemblo. About thirteen hundred people were evacuated from it, and five homes burned.
>
> The warning that went out was an ES-Alert: the same message to every phone in the area. It could not tell the coordinator who had left, who could not move, or who never got it.

*(Sources: Tribuna de Ávila and Ávilared, 23 July.)*

## 2. Where the fire is heading (0:20–1:00)

*Dashboard in replay mode. Press play; the satellite hotspots advance east.*

> These are Deepfire's satellite hotspots from that day. From them we estimate where the front is heading, hour by hour.
>
> At 15:30, using only the hotspots seen up to then, the forecast puts La Atalaya in the fire's path. The first hotspot within three kilometres of it came at 21:38. That is **about six hours** of lead time, computed from satellite data alone: between five and eight depending on the distance you measure from, because one satellite pixel decides the arrival. It says nothing about when anyone was warned.

*Point at the lead-time card and the "Where the fire is heading" panel.*

## 3. The order and the call (1:00–2:00)

*Evacuation orders panel.*

> The coordinator sees one proposed order per zone. For La Atalaya: leave for San Martín de Valdeiglesias, the nearest safe town the forecast does not reach. They approve it. For El Tiemblo, where the official order that day was to stay indoors because of the smoke, they can give exactly that.

*A phone rings in the room: the agent calls a resident of La Atalaya (Spanish).*

> **Agente:** Hola, buenas. ¿Hablo con…? … La orden para La Atalaya es salir ahora hacia San Martín de Valdeiglesias…
> **Vecina:** Mi madre no puede andar.

*The pin turns red, the resident appears in the rescue queue, the crew alert appears (and, with Twilio, an SMS reaches the crew phone).*

> She can't leave on her own. The agent understood that from what she said, not from a keyword. The coordinator now knows, and so does the fire crew, with the route from the El Tiemblo fire station.

**If the call fails:** click the pin → *Typed answer (backup)* → type "Mi madre no puede andar" → *Classify and record*. Without an LLM, press *Needs rescue*. See the [runbook](runbook.md).

## 4. The coordinator (2:00–2:20)

> Every resident who can leave on their own is sent on their way. Every one who can't lands here: the rescue queue, ordered by how soon the fire reaches them, each with the crew's route.

*Show the rescue queue and click "Show crew route". If #10 is ready: ask the agent by voice "¿Qué rescates tengo y en qué orden?"*

## 5. What changes, side by side (2:20–2:42)

*Slide: the figures of the day, then the table.*

> That day, the fire burned about thirty-eight thousand hectares in Ávila. Fifteen hundred people were evacuated, five homes were destroyed, and two hundred and twenty-nine more stood inside the burned area.
>
> We can't rerun that day. What HackFire changes is what the coordinator knows, and when.

| | 23 July 2026 | With HackFire |
|---|---|---|
| The warning | One ES-Alert to every phone: stay indoors because of the smoke | An order per zone, approved by the coordinator, said to each household by name |
| Answers | None: an alert cannot hear back | Every call ends in a status: leaving, needs rescue, or no answer |
| Who can't leave | Not known from the alert | On the coordinator's map within 2 seconds of being recorded, queued by when the fire arrives |
| The way out | The same message whatever the road | A route per home that avoids the fire and every road the coordinator marks as cut |
| Time to act | | La Atalaya flagged about 6 hours before the first hotspot nearby (5 to 8 depending on the distance), from satellite data alone |

*Sources for the left column and the figures: [press figures](../findings/2026-09-19-press-figures.md) (Junta de Castilla y León via Ávilared, 21 Aug; Tribuna de Ávila, 23 Jul; Idealista's estimate via Ávilared, 31 Jul). "2 seconds" is how often the dashboard refreshes the triage (`useTriage`, `POLL_MS`); the lead time is the replay's ([finding](../findings/2026-09-19-lead-time.md)). No "would have" figures: nobody can measure what a different warning would have changed that day.*

## 6. Roadmap (2:42–2:52)

> Next: real phone lines, and handing a call to a person at the control post when the agent should not carry it alone. Then more regions, inside the crews' and 112's own workflow, and a forecast that Devin retrains against every new fire's satellite data, with what residents tell us in each call.

| Now (this weekend) | Next | Then |
|---|---|---|
| Forecast from satellite hotspots, orders, calls in Spanish, triage, rescue queue, crew plan, road closures, live map for crews (Vonage) | A SIP trunk for real calls; handover to a human at the control post (SLNG `transfer_call`); road closures from the DGT's feed; a pilot in one municipality with a voluntary registry | Any area Deepfire covers, in more languages; inside 112 and the crews' dispatch; Devin iterating the spread model against real hotspots, validated fire by fire; call feedback growing the triage evaluations (Galtea) |

## 7. Close (2:52–3:00)

> This doesn't replace ES-Alert; it listens back. Every resident who evacuates on their own is a rescue the firefighters don't have to make.

## Questions to prepare

| Question | Short answer |
|---|---|
| Why not ES-Alert? | It broadcasts and doesn't listen. We hold a conversation with each resident and feed the answers back to the coordinator. Complementary |
| No coverage in a fire? | We call on the forecast, hours ahead. "No answer" is itself a signal. (In the late-July fires 16 municipalities lost coverage, The Objective, 29 July; not broken down by fire) |
| How good is the forecast? | A cone from the front's velocity over the last hours of hotspots, with no wind or terrain. Deepfire's own simulation cannot replay a past date; in live mode it can |
| Where do the phone numbers come from? | A voluntary municipal registry, complementary to ES-Alert. Numbers never leave the backend |
| Catalan? | SLNG's catalogue lists it; the demo is in Spanish because the residents are |
| What did the authorities do? | We don't claim anything about their timing; we don't have it |
