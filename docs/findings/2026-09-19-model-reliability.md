# How reliable the spread model is: what we measured, and what it does and does not show

**Date:** 2026-09-19 · **Area:** predicted spread, pitch figures (#4, #5, #15)

## What happened

We asked the spread model the questions a statistician would ask before anyone builds on it or puts a number on a slide: does it look at the future, does it beat simple rules, are its times calibrated, where does it fail, and how much data stands behind each claim. Everything was computed **outside the repository**, from the cached files in `data/`. Nothing in the product changed.

**Verdict.** The model is a proof of concept with useful discrimination (AUC 0.84) and a robust headline: a 6.1 h lead time at La Atalaya, against 1.1 h for a fixed-radius rule. It is **not statistically demonstrated**. It rests on one fire, about four independent waves of arrivals, and constants chosen while looking at that fire. It warns about far more places than the fire reaches, its predicted minutes are not calibrated, and its edge over "the nearer to the fire, the riskier" cannot be told apart from zero.

## How it was measured

- **Forecasts.** The model as shipped (`backend/app/spread.py`), rebuilt every 30 minutes from 22 Jul 15:00 to 24 Jul 16:00 UTC (the shipped file covers 23 July only), using only hotspots observed up to each moment. It never sees the future (`backend/tests/test_spread.py`). The rebuilt forecasts match the shipped file's in 43 of 44 issues; the difference is the 30 m simplification.
- **The question.** At each 30-minute moment, for each zone not yet reached: *will the fire come within 3 km of the zone's outline in the next H hours?* H = 6 and H = 3. Zones: the 57 in `data/zones.geojson` that are not roads (roads are reached trivially); 5 were already reached before the window and are dropped.
- **An alert** is the product's own rule (`backend/app/impact.py`): the latest forecast issued in the last 3 hours, its minutes counting down.
- **Ground truth.** A hotspot within 3 km of the zone's outline **and connected with the fire**: at least 3 other hotspots within 5 km and ±1 h. This matters. 10 of the 7,068 hotspots are isolated, and they change the first "arrival" of 11 of the 57 zones. Example: four care homes and a health centre in San Martín de Valdeiglesias were "reached" at 18:08 UTC on 23 July by a single MTG pixel, with the next hotspot 13.8 km away; the same pixel reappears at the same place 14 hours later. It looks like a fixed heat source or a spurious detection (not verified).
- **Static rules** (the comparison): the same footprint grown in every direction at a fixed 1 km/h or 3 km/h, with no direction and no memory of speed. A stand-in for fixed-radius alert zones, **not** what the authorities actually do.
- **Uncertainty.** Bootstrap over 12-hour time blocks (the alerts are strongly autocorrelated: 0.92 at 30 min, 0.67 at 2 h, 0.31 at 4 h, -0.12 at 6 h). There are only 5 blocks, so the intervals are wide.

## Results

### The headline holds up

| | Value |
|---|---|
| Lead time at La Atalaya (3 km rule) | **6.1 h** (flagged 13:30, fire within 3 km at 19:38 UTC) |
| Across 11 variants of the model's constants | **5.6 to 7.1 h** |
| The 1 km/h static rule | flags La Atalaya 18:30 UTC, **1.1 h** ahead |
| El Tiemblo, model vs 1 km/h static rule | 4.6 h vs 3.6 h |

The 3 km/h static rule flags La Atalaya and El Tiemblo from the very first moment of the window (28.6 h and 27.1 h ahead) and 52 of the 57 zones at some point, which is no warning at all.

### Zone by zone

Of the 57 zones, **18** were reached by the connected fire inside the window, **30** never were, 4 were reached only after the window closed and 5 before it opened.

| | |
|---|---|
| Reached, with a continuous warning before | **17 of 18** (94%) |
| ... at least 1 h of warning | 16 of 18 (89%) |
| ... at least 3 h | 10 of 18 (56%) |
| ... at least 6 h | 4 of 18 (22%) |
| Median warning over the 18 | **4.6 h** |
| Reached without warning | 1: the health post in Villanueva de Ávila (23 Jul 19:18 UTC) |
| Flagged at some point | 52 of 57 |
| Flagged and **never reached** | 30 (58% of the flagged): **1.7 extra zones per zone correctly warned** |

### Every 30 minutes, every zone (4,620 zone-moments)

| H = 6 h | TP | FP | FN | Precision | Recall | F2 |
|---|---|---|---|---|---|---|
| **Cone model** | 178 | 705 | 40 | 20.2% | 81.7% | **0.507** (95% CI 0.23 to 0.62) |
| Static 1 km/h | 166 | 976 | 52 | 14.5% | 76.1% | 0.412 |
| Static 3 km/h | 218 | 3,257 | 0 | 6.3% | 100% | 0.251 |

Against the 1 km/h rule the model has **23% fewer misses and 28% fewer false alarms**, so it wins whatever a miss costs relative to a false alarm. Against the 3 km/h rule, which never misses because it warns everyone, the model wins only if a miss is less than about 64 times as costly as a false alarm (40·r + 705 < 3,257). That ratio is a policy choice, which is why a person approves the calls.

At H = 3 h the model is weak: recall 47% (95% CI 0 to 74%), 85% of the alerts are false, F2 0.333 (static 1 km/h: 0.141).

### Is it better than the significance bar?

A paired permutation test on the F2 difference (swapping the two rules' forecasts inside 12-hour blocks; H0: no better than the static rule; one-sided, alpha 0.05):

| | vs static 1 km/h | vs static 3 km/h |
|---|---|---|
| H = 6 h | difference +0.095, **p = 0.062** | +0.256, p = 0.031 |
| H = 3 h | difference +0.192, **p = 0.094** | +0.126, p = 0.031 |

**H0 is not rejected against the relevant rival.** The direction of the effect is consistent, but with 5 blocks the smallest attainable p is 0.031, and with four tests a Bonferroni threshold is 0.0125, which none passes. Finer 6-hour blocks give smaller p-values (0.008 for H = 6 h) only because they understate the autocorrelation. To detect a difference of about +0.07 with 80% power, roughly **15 to 19 independent blocks** are needed; we have 4 to 6.

### Does the direction add anything?

AUC for ranking the zone-moments by risk (event within 6 h):

| Score | AUC (95% CI) |
|---|---|
| Model's predicted minutes | **0.838** (0.698 to 0.923) |
| Distance to the recent hotspots only | 0.793 (0.691 to 0.890) |
| Difference | +0.045 (-0.062 to +0.069) |
| Minutes, with distance as tie-break | 0.870 |

The model discriminates well, but its advantage over plain distance is not established. The two carry different information: combining them helps.

### Is the predicted time calibrated? No

| Predicted minutes to impact | Alert-moments | Fire arrives within 6 h |
|---|---|---|
| under 1 h | 27 | 11% |
| 1 to 2 h | 131 | 9% |
| 2 to 3 h | 66 | **80%** |
| 3 to 4 h | 123 | 18% |
| 4 to 5 h | 157 | 18% |
| 5 to 6 h | 379 | 16% |

There is no monotone relation between what the model says and what happens. At night only 9% of the alerts come true, against 22% by day.

### Where and when it fails

Performance is not homogeneous. By 12-hour block (UTC): recall 53% (23 Jul 03:00), **95%** (23 Jul 15:00, the run towards La Atalaya), 83% (24 Jul 03:00); the first block (22 Jul 15:00) has no events and 38 false alarms. 44% of all events fall in one block. The 18 arrivals form **4 waves** (1, 8, 3 and 6 zones), so the effective sample is closer to 4 than to 4,620.

### Why: the mechanism

Comparing what the model assumed with how far the leading edge really moved 2 to 3 hours later (81 forecasts; the satellite gap on the afternoon of 23 July prevents measuring the acceleration, so this describes mostly slow phases):

- **Speed.** The model is too fast by more than 1 km/h in 63% of the cases (median +1.16 km/h). Rank correlation with the real speed: 0.50.
- **Heading.** Median absolute error 61 degrees; only 39% within 30 degrees. When the front barely moves, the heading is noise.

### Data

617 of the 7,068 hotspots (8.7%) are LOW confidence. Dropping them makes the model worse (F2 0.507 to 0.473): they carry signal.

## Does re-tuning help? No

A grid of 81 settings (speed floor, look-back, peak decay, flank spread), tuned on one half of the fire and tested on the other (split at 23 Jul 18:00 UTC), in both directions. The correlation between how well a setting does in each half is **+0.17**. The setting that wins in training loses up to 0.18 of F2 outside it, and the shipped constants rank 2nd and 14th of 81 on the held-out half. Tuning on this fire mostly fits noise, and the shipped constants sit on a plateau. That does not validate them on other fires: they were chosen looking at this one and were not held out.

## Two small changes tested

| Change | F2 at 6 h (all / early half / late half) | Verdict |
|---|---|---|
| As shipped | 0.507 / 0.565 / 0.465 | |
| **Ignore isolated hotspots** when building the forecast | 0.534 / 0.565 / 0.504 | Better in one half, equal in the other; La Atalaya's lead unchanged (6.1 h). A data-hygiene fix, not evidence of skill: the ground truth ignores the same pixels, so part of the gain is circular |
| Night speed x0.5 | 0.533 / 0.595 / 0.488 | Better at 6 h in both halves but **worse at 3 h in the late half** (0.186 to 0.131). Not recommended |

## What we do about it

**Now, without touching the product:** this finding, and [the Q&A for the jury](../demo/reliability-qa.md), which says the same in plain words and lists what not to claim.

**Optional, UI only (prepared, not applied).** Two small changes that make the panels say no more than we know. See the patch at the end.
1. An "early warning" note under the zones list: the panel flags more places than the fire reaches, on purpose, and the coordinator decides who is called.
2. Predictions shown to the hour (`~4 h`, `< 1 h`), not to the minute (`35 min`), in the zones panel and the orders panel. The rescue queue and the crews' plan still show exact minutes; decide separately whether they should follow.

**After the hackathon**, each with a success criterion a non-statistician can check, and none of them validated on this fire:

| Change | Success looks like |
|---|---|
| Rank the zones by risk (predicted minutes plus distance), instead of a yes/no | Reviewing the top five zones covers at least 80% of the arrivals |
| Show alerts as bands ("within 6 h") where the minutes are not calibrated | The panel never says "in 1 h" when only 1 in 10 such alerts comes true |
| Model the day/night cycle | The night hit rate approaches the daytime one, on fires not used to design it |
| Use the heading only when the front demonstrably moves | Heading error on moving fronts stays low without hurting still ones |
| Add wind, terrain and fuel | Beats the current model held out, fire by fire |
| Ignore isolated hotspots (needs `pnpm data:spread`, `data:lead-time`, `data:routes --refresh` and `pnpm check:routes` afterwards) | Lead time and routes unchanged where they were sound |

**Validation protocol for any of them:** freeze the constants, the primary metric (F2 at 6 h plus AUC) and the thresholds before looking at results; validate leaving one **fire** out at a time; resample by 12-hour block and report the effective sample size, not the 4,620 zone-moments; correct for multiple comparisons; always compare against two references, the static rule and the distance rule. The Deepfire hotspot history goes back to January 2025.

**Do not:** re-tune the constants on this fire; drop the LOW-confidence hotspots; claim significance against the static rule; say "reliable" without an interval.

## Limits of this analysis

- **One fire, two days**, and the constants were chosen while looking at it.
- **Satellites are a proxy.** "Reached" means a hotspot within 3 km of the outline, seen by sensors with 375 m to 3 km pixels and a gap of about 2.5 hours on the afternoon of 23 July. Which pixels count as "connected" (3 neighbours, 5 km, 1 h) was chosen by us; its sensitivity was not tested.
- **Zones near each other are correlated**, which the time-block bootstrap does not capture.
- **The scripts are not in the repository.** They ran in a temporary folder. The definitions above are enough to redo the analysis; putting it in the repo as a reproducible, tested script is a separate piece of work.
- **The zone-moment counts are not independent samples.** Read the intervals, not the counts.

## Proposed UI change (not applied)

Verified on a clean copy of `main` at 6385b3b: the patch applies, `tsc` passes, `pnpm --filter frontend locales:check` passes (237 to 238 texts per language), the build passes and the lint warnings are the same three as before.

```diff
diff --git a/frontend/src/locales/en.json b/frontend/src/locales/en.json
index 0f45134..13d3eb5 100644
--- a/frontend/src/locales/en.json
+++ b/frontend/src/locales/en.json
@@ -170,7 +170,8 @@
     "showMore": "Show {count} more",
     "legendNow": "Now",
     "legendAhead": "6 h ahead",
-    "issued": "Forecast from {time}"
+    "issued": "Forecast from {time}",
+    "earlyWarning": "Early warning: it flags more places than the fire ends up reaching, on purpose. The coordinator decides who is called."
   },
   "leadTime": {
     "loading": "Loading the lead time…",
diff --git a/frontend/src/locales/es.json b/frontend/src/locales/es.json
index 3bbb4a7..ed6df29 100644
--- a/frontend/src/locales/es.json
+++ b/frontend/src/locales/es.json
@@ -170,7 +170,8 @@
     "showMore": "Ver {count} más",
     "legendNow": "Ahora",
     "legendAhead": "Dentro de 6 h",
-    "issued": "Previsión de {time}"
+    "issued": "Previsión de {time}",
+    "earlyWarning": "Aviso temprano: señala más lugares de los que el fuego llega a alcanzar, a propósito. El coordinador decide a quién se llama."
   },
   "leadTime": {
     "loading": "Cargando la antelación…",
diff --git a/frontend/src/ui/ZonesAtRisk.tsx b/frontend/src/ui/ZonesAtRisk.tsx
index 8bad8ae..2a6b444 100644
--- a/frontend/src/ui/ZonesAtRisk.tsx
+++ b/frontend/src/ui/ZonesAtRisk.tsx
@@ -41,6 +41,7 @@ export function ZonesAtRisk({ status, zones, hasForecast }: ZonesAtRiskProps) {
           {expanded ? t('fire.showFewer') : t('fire.showMore', { count: zones.length - VISIBLE })}
         </button>
       )}
+      <p className="note">{t('fire.earlyWarning')}</p>
     </>
   )
 }
diff --git a/frontend/src/ui/dashboard.css b/frontend/src/ui/dashboard.css
index 4c7701a..a11f874 100644
--- a/frontend/src/ui/dashboard.css
+++ b/frontend/src/ui/dashboard.css
@@ -1374,3 +1374,10 @@ button:active {
 .verdict.no-route {
   color: var(--alert);
 }
+
+.note {
+  margin: 12px 0 0;
+  font-size: 12px;
+  line-height: 1.4;
+  color: var(--text);
+}
diff --git a/frontend/src/ui/theme.ts b/frontend/src/ui/theme.ts
index b35de56..e1011f2 100644
--- a/frontend/src/ui/theme.ts
+++ b/frontend/src/ui/theme.ts
@@ -82,7 +82,9 @@ export function formatMinutes(minutes: number): string {
 
 /** `now` (the locale's word for it) or a duration: how the panel says when the fire arrives. */
 export function formatMinutesToImpact(minutes: number, now: string): string {
-  return minutes <= 0 ? now : formatMinutes(minutes)
+  if (minutes <= 0) return now
+  // A prediction is good to about an hour, not to the minute: "35 min" would claim more than we know.
+  return minutes < 60 ? '< 1 h' : `~${Math.round(minutes / 60)} h`
 }
 
 // Live fires: colour by hours since the last detection, radius by hours burning.
```

## Sources

- `data/hotspots_2026-07-22_24.geojson`, `data/spread_2026-07-23.geojson`, `data/zones.geojson`
- `backend/app/spread.py`, `backend/app/impact.py`, `backend/app/lead_time.py`, `backend/tests/test_spread.py`
- [The spread model](2026-09-19-spread-cone-model.md), [the lead time](2026-09-19-lead-time.md), [which press figures hold up](2026-09-19-press-figures.md)
