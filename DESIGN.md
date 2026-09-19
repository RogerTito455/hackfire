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
Phone (< 900 px)                    Wide screen (≥ 900 px)
┌──────────────────────────┐        ┌───────────┬──────────────────────────┐
│ (◆)(•) [Replay|Live](ES) │        │ replay    │ (logo HackFire)(• Online)│
│                          │        │ strip     │        [Replay|Live](ES) │
│           map            │        │───────────│                          │
│                          │        │ way out   │           map            │
│╭────────── ─── ─────────╮│        │ rescues   │                          │
││ ▶ time    slider       ││        │ orders    │                          │
││ [5][0][0][0]  strip    ││        │ fire      │                          │
││ way out, rescues, …    ││        │ alerts    │                          │
╰┴────────────────────────┴╯        └───────────┴──────────────────────────┘
```

- **The map is the screen.** It fills the viewport; everything else floats over it.
- **Top bar:** four pills clear of the notch: the logo, the connection dot, the mode toggle, the language. Under 480 px the brand name hides and the inactive mode shrinks to its icon, like a native segmented control.
- **Bottom sheet** ([`BottomSheet.tsx`](frontend/src/ui/BottomSheet.tsx)) with three heights, as in a maps app:
  - *peek* shows exactly the header (replay scrubber and status strip). It is measured, not fixed, so a longer language never cuts the strip.
  - *half* (52 % of the viewport) opens by itself when a resident is selected.
  - *full* (90 %).
  - Drag the handle, or tap it to cycle through the heights. Enter and Space work too.
- **Wide screens:** the sheet becomes a 400 px side panel on the left and the handle disappears.
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
- **Choosing a language:** the `ES`/`EN` pill in the top bar opens the phone's native picker. The first visit follows the browser's language and falls back to English; the choice is saved in `localStorage`.
- **Adding a language:**
  1. Copy `en.json` to `<code>.json` and set `_meta` (`name` in that language, `intl` as a BCP 47 tag such as `ca-ES`).
  2. Translate every value and keep the placeholders.
  3. Do the same for the backend's sentences in `backend/app/locales/` (no `intl` there).
  4. Run `pnpm check`.

  The new language appears in the picker with no code change.
- **`pnpm check` fails** (via [`scripts/check-locales.mjs`](frontend/scripts/check-locales.mjs)) when a locale misses a key or changes a placeholder, or when the code uses a key that `en.json` lacks.
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

## Revisions

- **2026-09-19, mobile redesign.** The earlier idea of a hi-vis yellow accent was dropped: yellow already means *freshly detected hotspot* on the map, and an accent in the same colour would read as fire. Blue took the "act here" role instead. Map mode labels were shortened to *Replay* and *Live* so the top bar fits a 320 px screen.
