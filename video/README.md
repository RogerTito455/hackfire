# HackFire presentation video

A 125-second 1920 × 1080 video for the pitch, made in code: [Remotion](https://www.remotion.dev) for the picture, ElevenLabs for the narration, the call's voices, the sound effects and the music. It does not record the dashboard. It draws its own interface, in HackFire's night palette and with the dashboard's icons, from the same data the dashboard uses.

```bash
pnpm video:studio    # preview and scrub it in the browser
pnpm video:render    # video/out/hackfire.mp4 (git-ignored)
```

## What it says

English narration with word-by-word subtitles; the call is in Spanish, subtitled in English. The script is [`src/script.json`](src/script.json), one entry per line.

| Chapter | Scenes | Shows |
|---|---|---|
| 01 The fire | `open`, `problem` | The real hotspots of 22–23 July on the map; the press figures; the ES-Alert of that day, quoted |
| 02 The forecast | `brand`, `forecast`, `leadtime` | HackFire and its pipeline; the rewind to 15:30, the forecast, and the 6 h 8 min lead time |
| 03 The call | `order`, `call`, `understood` | The coordinator approves the order; a simulated call with a demo resident; the triage it records |
| 04 The rescue | `rescue`, `command` | The rescue queue, the crew plan and the cached routes; asking by voice; the Vonage live map |
| 05 What changes | `compare`, `roadmap` | The day's cost, sourced; what the coordinator knows that day and with HackFire, side by side; the roadmap |
| 06 Listening back | `close` | ES-Alert speaks, HackFire listens back; the end card |

**Tone rules (CLAUDE.md) hold here too.** The comparison sets what the coordinator knew that day against what HackFire does, measured (the 2 s triage refresh, the replay's lead time); it never says what a different warning would have changed. Every figure has a source on screen or in `script.json`'s `about`: the press figures are the ✅ ones in [docs/findings/2026-09-19-press-figures.md](../docs/findings/2026-09-19-press-figures.md), and the ES-Alert text is quoted from Ávilared. The lead time comes with its definition, and says nothing about when anyone was warned. Everything from the order onwards is labelled "Simulation with demo residents", at the demo autopilot's times (`data/demo_timeline.json`).

## How it is built

- **Timing comes from the audio.** `pnpm video:voice` turns each line of `script.json` into one clip and writes [`src/data/narration.json`](src/data/narration.json) with its length and word timings (ElevenLabs `with-timestamps`). [`src/timeline.ts`](src/timeline.ts) lays the lines end to end, so rewording a line moves everything after it. Visual beats hang off words: `beat('leadtime-1', 'six')` is the frame "six" is said on.
- **One map, one camera.** [`src/FireMap.tsx`](src/FireMap.tsx) draws `src/data/map.json` in kilometres with a virtual camera, and [`src/MapStage.tsx`](src/MapStage.tsx) flies it from the valley to one street across the map scenes instead of cutting. `pnpm video:data` rebuilds `map.json` from `data/` with the backend's own route code (no network: cached routes).
- **The rest** is in [`src/Scenes.tsx`](src/Scenes.tsx) (the alert, the pipeline graph, the call, the command post, the close) and [`src/Chrome.tsx`](src/Chrome.tsx) (chapters, clock, subtitles). The call's waveform is the clip's real audio (`@remotion/media-utils`).
- **Sound.** Music ducks under speech; effects land on beats (`src/HackFireVideo.tsx`).

## Audio

`scripts/audio.ts` needs `ELEVENLABS_API_KEY` in the repo's `.env`, and spends the plan's characters, so it only regenerates what changed:

| Command | Writes | Regenerates when |
|---|---|---|
| `pnpm video:voice` | `public/audio/lines/*.mp3`, `src/data/narration.json` | A line's text, `say`, voice or settings change |
| `pnpm video:sfx` | `public/audio/sfx/*.mp3` | The file is missing |
| `pnpm video:music` | `public/audio/music.mp3` | The file is missing |

Voices: Christopher (narrator), David Martin (agent), Flavia (resident, filtered like a phone line). A line's `say` is a spelling for the voice only (`Burgo-ondo`), with the same number of words as its `text`. The generated audio is committed, so a render needs no key. Whisper was used to check every clip against its text.
