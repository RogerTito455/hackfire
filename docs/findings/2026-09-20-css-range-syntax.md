# The minifier wrote media queries the demo phone cannot read

**Date:** 2026-09-20 · **Area:** frontend build, demo phone

## What happened

On the Galaxy S9+ (Chrome 101) the dashboard had no phone layout: the top bar's words ran off the
screen, and the bottom sheet answered a swipe by changing `data-snap` while staying the height of
its header, so it looked like it opened and shut again. The same build was correct in every
desktop browser and in Playwright's Chromium.

## Why

Vite minifies CSS with esbuild, which rewrites `@media (min-width: 900px)` into the Media Queries
Level 4 range syntax `@media (width>=900px)` when the target allows it. That syntax is Chrome 104.
Chrome 101 cannot parse the condition, so it **drops the whole at-rule**: every responsive rule in
`dashboard.css` disappeared from the phone, while the source had them all along.

```
$ grep -o "@media[^{]*" dist/assets/dashboard-*.css | sort | uniq -c
      8 @media (width>=900px)
      1 @media (width<=899px)
```

## The fix

`frontend/vite.config.ts`:

```ts
build: { cssTarget: 'chrome101' }
```

The bundle then keeps `@media (min-width:900px)`, and the phone gets its layout back.

## How to check it again

```bash
pnpm --filter frontend build
grep -o "@media ([a-z-]*: *[0-9]*px)" frontend/dist/assets/dashboard-*.css | sort | uniq -c
grep -o "color-mix(\|[0-9]dvh" frontend/dist/assets/*.css   # each needs a plain fallback before it
```

Both `dvh` and `color-mix()` are still in the bundle on purpose: each has a `vh` or plain-colour
declaration immediately before it, which is what Chrome 101 uses.

## What it cost

Every phone check before today was run against a build whose responsive rules the phone never
applied. Re-check anything that was called "verified on the S9+" before 2026-09-20 12:00.
