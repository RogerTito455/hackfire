# Vonage Video

**Used for:** extension 2 (#18): a resident who needs rescue shows the coordinator live video, anchored to their pin, with live captions in Spanish.
**Status:** built and tested with a fake provider; not yet run against the live API (waiting on the application id).
**Owner:** Roger

## Access

https://developer.vonage.com → Dashboard → **Build → Applications → Create a new application**: generate the public and private key (downloads `private.key`), turn on **Video** (and **Messages** for the SMS), create it, and copy its **Application ID**. The account has free trial credit and test video minutes. On a trial, SMS reaches only the numbers on its allow list.

| Variable | Value |
|---|---|
| `VONAGE_APPLICATION_ID` | The application's id |
| `VONAGE_PRIVATE_KEY` | Locally, a path to the key file (relative paths start at the repo root; `*.key` is git-ignored). On Railway, the PEM text itself |
| `VONAGE_SMS_FROM` | Sender name; default `HackFire` |

## In the app

- `backend/app/providers/vonage.py` is the only module that imports `vonage` (Python SDK 4.9): routed sessions, client tokens, live captions and SMS through the Messages API.
- `backend/app/rescue_video.py`: one routed session per resident; a single-use link (`/v/<id>`) texted to the resident's registry phone; publisher token on first open, then 410; subscriber token for the coordinator once the resident is on camera. `/api/reset` forgets it all.
- Endpoints: `GET /api/video` (capabilities), `POST /api/rescues/{id}/video` (link + SMS), `GET /api/video/{link}` (resident), `GET /api/rescues/{id}/video` (coordinator). The backend serves the dashboard for `/v/<id>`.
- Frontend: `services/videoCall.ts` is the only file that knows `@vonage/client-sdk-video` (loaded on first use). The resident page publishes the back camera with `publishCaptions`; the dashboard subscribes with `subscribeToCaptions` and shows the stream in a card anchored to the resident's pin, the latest caption under it. **Request live video** is on each rescue in the queue.

## Gotchas

- **The Python SDK cannot start `es-ES` captions**: its language enum lacks it, although the REST API supports it. `start_captions` posts to `/v2/project/{application_id}/captions` through the SDK's own HTTP client; a 409 (already running) counts as success.
- Captions need a **routed** session, a publisher with `publishCaptions: true`, and a moderator token in the start call.
- Camera access needs **HTTPS** (Railway has it; plain `http://` on a phone does not work).

## Sources

- https://developer.vonage.com/en/video/getting-started
- https://developer.vonage.com/en/video/guides/live-caption
- https://github.com/Vonage/vonage-python-sdk/tree/main/video
- https://developer.vonage.com/en/messages/code-snippets/sms/send-sms
