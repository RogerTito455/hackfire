# How reliable is it? Plain words for the jury, and the hard questions

For the three-minute pitch ([pitch.md](pitch.md)) and the questions after it. The jury is not made of statisticians, so this page says what we measured in words anyone can repeat, and where the honest limits are. The method, the full numbers and the intervals are in [the finding](../findings/2026-09-19-model-reliability.md); keep them for the technical mentors.

Tone, as everywhere: this was a real fire and people lost their homes. **No "we would have saved…", and nothing about when the authorities warned anyone.** We only compare the system with satellite data and with simple rules.

## Four messages (say these, and only these, as claims)

1. **"At La Atalaya we flagged the danger 6 hours before the fire came within 3 km."** It stays between 5.6 and 7.1 hours across the 11 model settings we tried. (Lead time: [how it was computed](../findings/2026-09-19-lead-time.md).)
2. **"Of the 18 places the fire reached in two days, 17 had a warning before, for a median of 4.6 hours."** The one that did not was a health post in Villanueva de Ávila.
3. **"It is a smoke alarm: sensitive on purpose."** For each place it warns correctly it also flags about two that the fire never reaches. That is why no call goes out until the coordinator approves it. A needless call costs a call; a missed warning costs far more.
4. **"A fixed-radius rule would have flagged La Atalaya 1 hour ahead. We flagged it 6 hours ahead."** The comparison is easy to understand and it was measured the same way for both.

## Slide (one, if there is room)

> **Early warning, with a person in the loop**
> - La Atalaya flagged **6 h** before the fire came within 3 km (5.6 to 7.1 h across the 11 settings we tried). A fixed-radius rule: 1 h.
> - 17 of the 18 places the fire reached were warned first. Median warning: **4.6 h**.
> - It warns about twice as many places as the fire reaches, so the coordinator decides who is called.
> - One real fire so far. Next: test it on other fires.

## Hard questions, short honest answers

**Do you trust the model?**
It is an early warning measured in hours, not an exact prediction. It warns about more places than the fire reaches, so a person decides. We trust it to say "get ready", not to say "leave now".

**What if it is wrong?**
It is a complement to ES-Alert and the 112, not a replacement. In this fire, 1 of the 18 places reached had no earlier warning from us, and the official channels are still there.

**Is it validated?**
On one real fire, without letting it see the future. Not on others yet. That is the next step, and we say it before anyone asks.

**Why not just use a fixed radius around the fire?**
We tried that as a comparison: a rule that grows the fire evenly in every direction flags La Atalaya 1 hour ahead, ours 6. And a wider radius warns almost everyone, all the time.

**Why so many false alarms?**
On purpose, and it is a measured trade-off: for every place correctly warned we flag about two more. Warning less would miss places the fire really reaches. The coordinator approves before any resident is called, so the cost of a false alarm is bounded.

**Is it better than a simple rule in a statistical sense?**
Better on both kinds of error against the fixed 1 km/h rule (23% fewer misses, 28% fewer false alarms), but with one fire the difference is not yet statistically significant. Enough data to settle it means several more fires.

**Is it cost-effective?**
We do not claim savings: we have no data for that. What we can measure is what a call costs and how many lines it takes to call a whole neighbourhood inside the warning time. Those numbers are still being measured (#14); do not quote a figure until the finding has it.

**Did you tune it on this fire?**
Yes, the constants were chosen while looking at it. We checked that re-tuning on half the fire does not beat the current settings on the other half: they sit on a plateau. That does not make them validated on new fires, and the honest description stays "one fire, tuned on it".

## Say this if you only have one sentence

> "One real fire, tuned on it: it gave La Atalaya 6 hours of warning, it warns about twice as many places as it should, and that is why a coordinator approves every call. The next step is other fires."

## Do not say

- "Mathematically proven", "certified", "statistically significant" or "p < 0.05". It is not: p = 0.06 against the strongest simple rule.
- "Reduces detection or response time compared with today's operations." We have no data on the authorities' times.
- "It saves lives" or any figure of savings or return on investment.
- "It predicts when the fire arrives." It gives an early warning of hours; the minutes it shows are not calibrated.
- "Reliable" without saying "on one fire".
- Any press figure that is not in [the checked list](../findings/2026-09-19-press-figures.md).

## Backup for technical mentors

| | Value |
|---|---|
| Every 30 min, every zone, 6 h question | TP 178, FP 705, FN 40; precision 20%, recall 82%, F2 0.51 (95% CI 0.23 to 0.62) |
| Static 1 km/h and 3 km/h rules, same question | F2 0.41 and 0.25 |
| Significance vs static 1 km/h | paired permutation on 12 h blocks, p = 0.062 (6 h), 0.094 (3 h); 15 to 19 independent blocks needed for 80% power |
| Discrimination (AUC) | model 0.84 (0.70 to 0.92), plain distance 0.79 (0.69 to 0.89), difference not distinguishable from zero |
| Calibration of the predicted minutes | not monotone: 9 to 11% of "under 2 h" alerts come true, 80% of "2 to 3 h", 16 to 18% of "3 to 6 h" |
| Night vs day | 9% vs 22% of alerts come true |
| Effective sample | 18 arrivals in 4 waves; 5 usable 12 h blocks |
| Does re-tuning generalise? | no: correlation of +0.17 between halves across 81 settings |

Definitions and caveats are in [the finding](../findings/2026-09-19-model-reliability.md). Nothing here was run from the repository's own scripts; say so if asked.
