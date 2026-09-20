# Voice latency: the model answers a turn in about one second

**Date:** 2026-09-20 · **Area:** voice track, demo (#14)

## The numbers

Four turns of a resident call, against the same model the voice agent thinks with, through SLNG's Context Router:

| Turn (what the resident says) | Model answer time |
|---|---|
| "Sí, soy yo. ¿Quién es?" | 1.01 s |
| "Vale… ¿y por dónde salgo?" | 0.89 s |
| "Somos tres en casa." | 0.65 s |
| "Mi madre no puede andar." | 0.96 s |

**Minimum 0.65 s, median 0.92 s, maximum 1.01 s.** Model: `bedrock-mantle/nvidia.nemotron-super-3-120b:latest`, region `eu-north`.

## How it was measured

A script sent the resident agent's real prompt (`voice/resident/instructions.md`) and the call's template variables (resident, address, fire status, route) to `POST /v1/chat/completions` on the router, keeping the conversation, and timed each request from send to full answer. No tools were attached, so nothing was recorded anywhere.

Two details worth knowing:
- The router **requires the prompt's template variables**; without them it answers `422 missing_template_variables`.
- It does not accept `max_tokens`; that also gives a 422.

## What this is, and what it is not

- **It is the thinking time only**, a floor for the turn latency a resident hears.
- **The full turn adds** speech recognition, the text-to-speech voice (Deepgram Aura 2), the audio round trip and, when the agent calls a tool, our own API (`/tools/report_status` answers in milliseconds locally, more from Railway).
- **Not measured:** the end-to-end silence a person hears between finishing their sentence and hearing the agent. That needs one real browser call with a stopwatch, or SLNG's own call timings. Do it in the rehearsal and add the number here.
