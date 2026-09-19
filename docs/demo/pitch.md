# Pitch script (draft)

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
> At 15:30, using only the hotspots seen up to then, the forecast puts La Atalaya in the fire's path. The first hotspot within three kilometres of it came at 21:38. That is a lead time of **six hours and eight minutes**, computed from satellite data alone. It says nothing about when anyone was warned.

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

## 4. The coordinator (2:00–2:30)

> Every resident who can leave on their own is sent on their way. Every one who can't lands here: the rescue queue, ordered by how soon the fire reaches them, each with the crew's route.

*Show the rescue queue and click "Show crew route". If #10 is ready: ask the agent by voice "¿Qué rescates tengo y en qué orden?"*

## 5. Close (2:30–3:00)

> Six hours of lead time, from satellites alone.
>
> A call needs a network, just like ES-Alert does. That is why we call when the forecast flags a zone, hours before the fire arrives, while the towers still work. And a call nobody answers is information too: it tells the coordinator where to send a patrol.
>
> This doesn't replace ES-Alert; it listens back. Next: live video from residents who need rescue, volunteers dispatched only under the coordinator's orders, and a spread model that improves itself against the real hotspots.
>
> Every resident who evacuates on their own is a rescue the firefighters don't have to make.

## Questions to prepare

| Question | Short answer |
|---|---|
| Why not ES-Alert? | It broadcasts and doesn't listen. We hold a conversation with each resident and feed the answers back to the coordinator. Complementary |
| No coverage in a fire? | We call on the forecast, hours ahead. "No answer" is itself a signal. (In the late-July fires 16 municipalities lost coverage, The Objective, 29 July; not broken down by fire) |
| How good is the forecast? | A cone from the front's velocity over the last hours of hotspots, with no wind or terrain. Deepfire's own simulation cannot replay a past date; in live mode it can |
| Where do the phone numbers come from? | A voluntary municipal registry, complementary to ES-Alert. Numbers never leave the backend |
| Catalan? | SLNG's catalogue lists it; the demo is in Spanish because the residents are |
| What did the authorities do? | We don't claim anything about their timing; we don't have it |
