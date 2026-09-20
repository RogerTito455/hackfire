# HackFire design

How the dashboard looks and why. Change the look in `frontend/src/ui/` only: logic in `domain/` and `hooks/` never imports a colour, a size or a word. Scope and decisions stay in [PLAN.md](PLAN.md).

## Who it is for

An emergency coordinator on a phone, outdoors, in a hurry, maybe in sunlight or at night. They need to see three things at a glance: where the fire is, which residents need something, and each resident's way out. Most sessions are on a phone and not installed as an app (no PWA), so the page has to feel like a native maps app inside a mobile browser, down to old ones (Galaxy S9+, Chrome 101).

## The idea: civil-protection signage

The look borrows from emergency signage rather than from a SaaS dashboard. Every colour means something, and nothing is coloured for decoration.

| Colour | Means | Where |
|---|---|---|
| Warm (yellow → orange → red → brown) | The fire | Hotspots by age, predicted spread, time-to-impact figures |
| Civil-protection blue | The way out, and what you can do | Routes, primary buttons, the selected resident, focus rings |
| Four status colours | People | Map markers, the status strip, triage buttons |
| Navy | Text and surfaces | Ink, night-blue dark mode |

The blue is the international civil-defence sign's blue, so the route never competes with the fire for attention: warm means danger, blue means safety. Status colours always come with an icon, so no state depends on telling colours apart.

### One loud element

The **status strip** is the only element that shouts: four tiles with big numerals (28 px, weight 800). A tile with people in that state is filled with its colour; an empty one is white with a coloured outline. Everything around it stays quiet: sentence-case headings, hairline lists, no gradients, no decorative shadows.

## Tokens

CSS variables live in [`ui/theme.css`](frontend/src/ui/theme.css); the values the map and the markers need in TypeScript live in [`ui/theme.ts`](frontend/src/ui/theme.ts).

### Colour

| Token | Light | Dark | Use |
|---|---|---|---|
| `--ink` | `#0f1b3d` | `#eef2ff` | Headings, numbers, body text on paper |
| `--ink-2` | `#4a5578` | `#a7b1d6` | Secondary text, empty states |
| `--paper` | `#ffffff` | `#141e42` | Groups, floating pills |
| `--mist` | `#eef2fb` | `#0b1330` | Sheet background, page |
| `--line` | `#d6ddee` | `#26325c` | Hairlines, outlines |
| `--route` | `#2447d6` | `#6f8cff` | The way out; primary actions |
| `--route-ink` | `#ffffff` | `#0b1330` | Text on `--route` |
| `--fire-1` … `--fire-4` | `#ffd23f` `#ff7a1a` `#e5301f` `#7a1f12` | same | Fire, fresh to old; time to impact |

| Status | Colour | Icon |
|---|---|---|
| Not called yet (`pending`) | `#64708f` | hourglass |
| Evacuating | `#0e9f6e` | exit |
| No answer | `#e9a100` | phone-missed |
| Needs rescue | `#e0302a` | lifebuoy |

Map ramps (`HOTSPOT_AGE_COLORS`, `SPREAD_HOUR_COLORS`, `ZONE_URGENCY_COLORS`) are in `theme.ts`. Zones at risk are purple so they never read as fire or as a route.

### Type

The phone's own typeface: SF Pro on iPhone, Roboto on Android (`-apple-system, BlinkMacSystemFont, 'SF Pro Text', system-ui, Roboto, 'Segoe UI', sans-serif`). A downloaded font would cost the old phone a second of blank text for no gain in legibility.

| Role | Size / weight |
|---|---|
| Status numerals | 28 px / 800, tabular |
| Group headings | 17 px / 700, sentence case |
| Body, buttons | 15 px |
| Inputs and selects | 16 px (below 16 px iOS zooms the page on focus) |
| Meta, labels | 11–13 px / 600–700 |

No all-caps labels and no eyebrows above headings. Times and counts use tabular figures so they do not jump while the replay plays.

### Shape and depth

Radius follows hierarchy: sheet 22 px, groups 14 px, controls 10 px, pills fully round. Only things floating over the map (the sheet, the top-bar pills, popups) cast a shadow (`--float`); nothing inside the sheet does.

## Layout

```
Phone (< 900 px)                    Wide screen (≥ 900 px): the console
┌──────────────────────────┐        ┌──────────────────────┬───────────────┐
│ (◆)(•) [Replay|Live](ES) │        │ HackFire • [Replay|Live]  (ES)       │
│                          │        ├──────────────────────┤               │
│           map            │        │ ▶ time slider                        │
│                          │        │ [5][0][0][0]  strip, data note       │
│╭────────── ─── ─────────╮│        ├──────────┬───────────┤     map       │
││ ▶ time    slider       ││        │ way out ◂│ the open  │               │
││ [5][0][0][0]  strip    ││        │ rescues 3│ section,  │               │
││ way out, rescues, …    ││        │ crews    │ at a size │               │
││ (every section stacked)││        │ …      ⟳ │ you read  │               │
╰┴────────────────────────┴╯        └──────────┴───────────┴───────────────┘
```

- **The map is the screen.** It fills the viewport; everything else floats over it.
- **A key on the map** ([`MapLegend.tsx`](frontend/src/ui/MapLegend.tsx)), because a red dashed road and a grey circled one are the same thing to anyone who did not build this: the hotspot and forecast ramps with their ends named, a place in the path, the way out, the road the fire reached, the road the coordinator closed, and the four resident states. It is open on a laptop, bottom left, and folded to its title on a phone, under the top bar — and folded as well once the divider leaves the map under 620 px, where an open key would be covering what it explains. Open, it never takes more than 38 % of the map's width.
- **Top bar:** four pills clear of the notch: the logo, the connection dot, the mode toggle, the language. Under 480 px the brand name hides and the inactive mode shrinks to its icon, like a native segmented control.
- **Bottom sheet** ([`BottomSheet.tsx`](frontend/src/ui/BottomSheet.tsx)) with three heights, as in a maps app:
  - *peek* shows exactly the header (replay scrubber and status strip). It is measured, not fixed, so a longer language never cuts the strip.
  - *half* (52 % of the viewport) opens by itself when a resident is selected.
  - *full* (90 %).
  - Drag the handle, or tap it to cycle through the heights. Enter and Space work too.
- **Wide screens: the console** ([`Console.tsx`](frontend/src/ui/Console.tsx)), not the sheet. The top bar becomes its header, the scrubber and the status strip sit under it across the whole width, and below them a rail names every section beside the one that is open:
  - the rail carries each section's icon, its name and a live count (rescues waiting, roads closed, orders written), so nothing the dashboard can do is a scroll away; the open one is marked with the same blue bar the landing uses for the step it is showing, and **Reset demo** sits at its foot.
  - the open section is a panel with room to be read, not a row in a list. Rail and panel together are 520 px, 632 px from 1200 px and 736 px from 1500 px; the map keeps the rest and is never covered.
  - selecting a resident on the map opens *Way out*, the way it opens the sheet halfway on a phone. Sections stay mounted while another is read, so a call or a video keeps running.
- **The divider decides the width** ([`ConsoleDivider.tsx`](frontend/src/ui/ConsoleDivider.tsx), [`useConsoleLayout.ts`](frontend/src/ui/useConsoleLayout.ts)). From 900 px the line between the console and the map can be dragged, because how much map a coordinator wants is not something a breakpoint knows.
  - **Bounds: 400 px to half the viewport.** Below 400 the rail and the open section stop being two readable columns; past half the map would be the smaller half, which is not what it is for. So the 520 / 632 / 736 above are starting points, not the last word: an untouched browser still gets exactly them.
  - The line is a hairline; the grip halfway down it is a 44 px target. It is a `role="separator"` with `aria-valuenow`, takes focus and shows the same 3 px ring as everything else: the arrows move it 16 px (64 px with shift) and Home and End jump to the bounds.
  - The map resizes with it: `TriageMap` takes the width as a prop and tells MapLibre to measure its box again.
  - The width is remembered per browser (`hackfire.console.width`), inside try/catch like every other stored choice.
  - Under 520 px the console tightens rather than break: the four states go two by two, the rail drops to 132 px, and the brand name folds to its mark so the mode toggle keeps its room in the header.
- **Map only.** A button in the map's top-right corner (*Map only*, and *Show the panel* to come back) puts the console away: the top bar spans the screen, so the mode, the language and the connection stay in reach, and the map takes everything under it. The button never moves and never hides, which is how you get back. The choice is remembered too (`hackfire.console.hidden`).
- **Each mode gets its own sections.** Rescues, the crew plan, closures, orders, the fire and the crew alerts all read the demo registry, so they belong to the replay; live mode shows the places the selected real fire reaches, and the activity log and service status, which both modes need. The reset belongs to the demo too.
- **Every section says what it is for** in one line under its heading, and the [`DataNote`](frontend/src/ui/DataNote.tsx) badge says where its numbers come from: a dashed outline for the demo registry, solid ink for data nobody here wrote, the same pair the alert drafts already use for draft and official.
- **Before a resident is picked**, *Way out* lists the registry ([`ResidentPicker.tsx`](frontend/src/ui/ResidentPicker.tsx)), each name with its status icon, so a resident can be reached without hunting for their pin under the smoke.
- **Groups** are native inset lists: one white rounded group per topic, rows separated by hairlines, not a wall of identical cards. The selected resident's group has a blue inset outline.
- Left-aligned text everywhere except the one-line hint under the groups.

## Mobile rules

- **Touch targets** at least 44 × 44 px.
- **Safe areas:** `viewport-fit=cover` plus `env(safe-area-inset-*)` on the top bar and the sheet.
- **`theme-color`** matches the paper colour in light and dark, so the browser chrome blends in.
- **No scroll chaining:** `overscroll-behavior` stops pull-to-refresh from firing inside the sheet.
- **The map's own zoom buttons** are hidden on phones (pinch replaces them), and the credits fold into the (i) button.
- **No machine translation:** `translate="no"`, because Chrome's translate bar would garble a page that already ships its languages.

### Old browsers (checked on a Galaxy S9+, Chrome 101)

- **No `dvh`** (it needs Chrome 108). The app is `position: fixed; inset: 0`, and every `dvh` height has a `vh` line before it. Without that the page renders 0 px tall.
- **No `color-mix()`** (it needs Chrome 111). Every use has a plain fallback declared first.
- **`ResizeObserver` and `Intl.PluralRules`** are fine from Chrome 64 onwards.
- **Test on the real phone:** `adb reverse tcp:5173 tcp:5173` and `adb reverse tcp:8000 tcp:8000`, then open `localhost:5173` on it. `chrome://inspect` gives you its console.

## Accessibility

- A visible focus ring on everything (3 px `--route`).
- `prefers-reduced-motion` turns transitions off.
- `prefers-color-scheme` switches to the night-blue palette.
- Icons are `aria-hidden`; the visible text or an `aria-label` names each control.
- The connection state is a `role="status"`, and its text stays readable by screen readers when phones show only the dot.
- Map markers are buttons named "<resident>: <status>".

## Motion

Only motion that answers a touch: the sheet sliding between heights (280 ms, `--ease-out`), buttons scaling to 97 % while pressed, and the map flying to a route. No entrance animations, no hover effects on cards.

## Languages

Every word the dashboard shows lives in [`frontend/src/locales/`](frontend/src/locales), one JSON file per language (English `en.json` is the reference). Components ask for text with `useI18n().t('section.key', vars)`; nothing in `ui/` hard-codes a sentence.

- **Placeholders:** `{name}`. Numbers passed as numbers are written the locale's way (1,234 or 1.234).
- **Plurals:** an object of `Intl.PluralRules` forms, picked by a numeric `count`: `{ "one": "{count} person", "other": "{count} people" }`.
- **Dates and numbers:** `useI18n().intl` (the `_meta.intl` tag) goes to the formatters in `theme.ts`. Fire and forecast times are shown in Spain's time zone; crew-alert clocks in the phone's own.
- **Choosing a language:** the flag pill in the top bar opens the phone's native picker, which lists every language by its own name. Flags live in `ui/flags/`, not `ui/icons/` (they are full-colour pictures, not the outline icon format), and load as separate files. The first visit follows the browser's language and falls back to English; the choice is saved in `localStorage`.
- **Adding a language:**
  1. Copy `en.json` to `<code>.json` and set `_meta`: `name` in that language, `intl` as a BCP 47 tag such as `ca-ES`, and `flag`, the name of a round-cropped square SVG in `frontend/src/ui/flags/` (optimise it first: `pnpm dlx svgo@3 --precision=1 --multipass <file>`).
  2. Translate every value and keep the placeholders.
  3. Do the same for the backend's sentences in `backend/app/locales/` (no `intl` there).
  4. Run `pnpm check`.

  The new language appears in the picker with no code change.
- **`pnpm check` fails** (via [`scripts/check-locales.mjs`](frontend/scripts/check-locales.mjs)) when:
  - a locale misses a key or changes a placeholder;
  - the code uses a key that `en.json` lacks;
  - text is typed straight into JSX or into an `aria-label`, `title`, `placeholder` or `alt`.

  Brand names are the only exception.
- **What is real is said on screen:** a line under the status strip (`DataNote`) and a block on the landing page say that the fire data is real and that the residents, calls and evacuations are fictional.
- **Sentences the backend writes** (route directions, evacuation orders, the fire line the agents say, crew alerts) live in `backend/app/locales/<code>.json` and are read with `i18n.t()` (`backend/app/i18n.py`). Every dashboard request sends `Accept-Language` from `<html lang>`, so they arrive in the dashboard's language; routes are cached as data and put into words per request. The voice agents and the crew SMS keep their own language (`HACKFIRE_AGENT_LOCALE`, `HACKFIRE_CREW_LOCALE`, English by default), whatever the dashboard shows. `tests/test_i18n.py` checks that the backend locales match.
- **Not translated:** data rather than interface: the lead-time definition, resident names, and the mobility notes the LLM extracts from what residents say.

## Checklist against generic design

Before merging a UI change, check that it does not bring back:

- all-caps eyebrow labels over headings;
- meta strings joined with "·" or "→" arrows appended to buttons; use commas, a second line or an icon;
- identical cards with one radius and one grey shadow everywhere;
- gradients or colour used as decoration. A colour here always means fire, way out or a status;
- an icon package or component kit (CLAUDE.md rules them out). Icons are hand-drawn, see [ui/icons/README.md](frontend/src/ui/icons/README.md);
- a downloaded font or a monospace font for data;
- a status shown by colour alone;
- hard-coded English in a component instead of a locale key.

## Landing page

`/about` (`frontend/about.html`, `src/landing.tsx`, components in `ui/landing/`) presents the project to judges and visitors and sends them to the dashboard at `/`. Same tokens, icons, languages and rules as the dashboard. It should read as a calm product page for emergency services, not a startup page:

- **Layout:** a 1120 px column on a 12-column grid, left-aligned. Sections are paper, separated by 1 px `--line` hairlines, with the same vertical rhythm (56 px on phones, 88 px from 720 px). Side headings take 4 columns and their content 8.
- **One dark section, the hero:** headline (32 / 48 / 56 px, weight 800, -0.02em), a lead at a 60-character measure, a solid blue button and a hairline outline button. On the right, the product itself: `public/dashboard-phone.webp` in a plain phone frame. The fire never sits behind text.
- **Controls 8 px, cards 12 px, no pills** (the language picker keeps its own). No glows, no gradients, no uppercase eyebrows, no "·" meta strings, no "→" arrows. Type scale 14 / 16 / 18 / 24 / 32 / 48.
- **Colour:** navy ink on white, one action blue (`#2447d6` for buttons). Fire colours appear only inside data (the mini-demo map, the lead-time window) and status colours only for the triage states.
- **Lead time is a range, not a count-up.** "About 6 hours of lead time", "between 5 and 8 hours depending on the distance used (2–5 km)", a timeline from the flag (15:30 CEST) to the first hotspot within 3 km (21:38 CEST) with the 2–5 km window shaded, the caveat that it comes from satellite data only, and why it is a range: one medium-confidence pixel decides the arrival, and the model was tuned on this fire. The figures are `PUBLISHED_LEAD_TIME` in `domain/leadTime.ts` (one row per radius, from the finding's table); `leadTimeRange()` rounds them. If `pnpm data:lead-time` ever changes them, update both.
- **How it works is a mini-demo** (`ui/landing/MiniDemo.tsx`) beside a numbered list of its four steps (above it on phones); the active step is marked by a blue bar and weight, and each step jumps to its moment. SVG, CSS and a small playhead, no map library. The map stays night-blue, like the product screen it stands for, inside a hairline frame. It loops about 25 s from 14:30 on 23 July, so the first frame already shows the fire: real hotspots fill the map, the predicted spread reaches La Atalaya and El Tiemblo, an example call plays out and the example residents' pins change state. It plays only while on screen and can be paused. Under reduced motion it shows the final frame. Its data (`miniDemo.json`, about 11 KB) is generated from `data/` by `pnpm --dir frontend data:mini-demo`; it says on screen that the residents and the call are examples.
- **The rest is restrained:** the three outcomes as a row with their status icon and a top rule in the status colour; the demo instructions as a numbered list beside the primary button; the stack as a definition list; the note on the real fire in small secondary text.
- **Thin scrollbars** come from `theme.css`, as on the dashboard.
- **It scrolls.** A sticky white top bar keeps **Open the demo** in reach on a phone.
- **No links to the repository**, which is private.

The dashboard picture is `frontend/public/dashboard-phone.webp`, a 390 × 780 screenshot at 2× of a local run with the sample registry, never the real one.

## Revisions

- **2026-09-20, density.** The situation strip took 260 px, a third of a 1366 x 768 laptop, before a single rescue was visible: the scrubber and the demo switch now share a line and each state is one line, which brought it to 185 px. Measured at 1920, 1600, 1440, 1366, 1280 and 1024.
- **2026-09-20, room for either side.** The console's width was whatever the breakpoint said, so on a laptop nobody could give the map more room than the stylesheet allowed. A divider now sets it, between 320 px and half the viewport, remembered per browser, and a *Map only* button puts the console away altogether. Phones are untouched, and a browser that has never been dragged still renders exactly as before.
- **2026-09-20, the console.** On a laptop the ten sections were stacked in one 460 px column, so half the dashboard was two scrolls away and nothing said what a section was for; and live mode kept showing the replay's sections, which put demo residents next to real fires. Wide screens now get the rail and one open section, every section carries a line of its own, and each mode shows only what it can honestly show. The phone keeps the bottom sheet exactly as it was, with the same two additions.

- **2026-09-19, mobile redesign.** The earlier idea of a hi-vis yellow accent was dropped: yellow already means *freshly detected hotspot* on the map, and an accent in the same colour would read as fire. Blue took the "act here" role instead. Map mode labels were shortened to *Replay* and *Live* so the top bar fits a 320 px screen.
- **2026-09-19, calm landing.** The loud landing (a 900-weight headline over glowing hotspots, a fire-coloured band with a counting lead time, colour fields in every section) read as a generic startup page. It became a paper page with hairlines and one dark hero, and the lead time became a range (about 6 hours, 5 to 8 depending on the radius) because one satellite pixel decides the arrival.
