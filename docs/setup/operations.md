# Operations: the audit log and the service status

Two things an operations room needs without a database: a record of every decision and outcome, and whether each external service is answering right now.

## Audit log

`backend/app/audit.py` keeps an append-only log in memory and in a JSON Lines file, one event per line.

- **File:** `HACKFIRE_AUDIT_FILE`, by default `data/audit.jsonl` (git-ignored). On Railway it lives in the container and is lost on a redeploy; mount a volume there to keep it.
- **Restart:** on start-up the backend reads the file back from its last `demo.reset` event, so the log survives a restart.
- **Reset:** *Reset demo* (`POST /api/reset`) never truncates the file. It appends a `demo.reset` event, and the dashboard and the API show the events from that one on. The file is the whole trail; the dashboard shows the current run.
- **No phone numbers.** Events name residents by name and id. A value named `phone` is dropped and any text that looks like a phone number (nine digits or more) is replaced with `[redacted]` before it is written. `tests/test_audit.py` runs a workflow on the sample registry and checks that no registry phone reaches the file.
- **Language:** an event stores a locale key (`action`) and its values, never text. `GET /api/audit` renders each one as a sentence in the request's language, from the `audit` section of `backend/app/locales/`.

Each event:

```json
{"id": "3f2a…", "at": "2026-09-19T21:04:11+00:00", "action": "status.reported", "actor": "agent",
 "source": "agent_tool", "subject": "n-001", "values": {"name": "…", "status": "evacuating", "people": 2}}
```

| Action | Actor | Logged when |
|---|---|---|
| `order.approved`, `order.approvedShelter`, `order.changed`, `order.changedShelter` | coordinator or autopilot | An order is approved or changed |
| `call.webStarted`, `call.phoneStarted`, `call.ended` | coordinator or system | A browser call starts, a campaign places a phone call, a call ends |
| `campaign.started` | coordinator | A zone's calls start, with calls placed and refused |
| `status.reported` | agent, coordinator, autopilot or system | A status is recorded. `source`: `agent_tool` (the voice agent's `report_status`), `typed_answer`, `manual_button` (the dashboard's buttons send `?via=dashboard`), `autopilot`, `safety_net` (a browser call ended with nothing recorded) or `campaign` (a phone call ended unanswered) |
| `alert.createdSms`, `alert.createdDashboard`, `alert.smsSent`, `alert.smsFailed` | system or autopilot | A crew alert is raised, and whether its SMS went out |
| `closure.added`, `closure.removed` | coordinator | A road is closed or reopened |
| `video.linkTexted`, `video.linkShown` | coordinator | A video link is created for a resident (the link itself is never logged) |
| `autopilot.on`, `autopilot.off` | coordinator | The call simulation is turned on or off |
| `demo.reset` | coordinator | The demo is reset |

The autopilot's changes are logged by comparing the state before and after each move of the slider: orders it approves, statuses it sets, alerts it raises. Scrubbing back, which undoes them, is not logged.

Endpoints:

- `GET /api/audit?limit=15` (1 to 1000): the current run, newest first, with `message`.
- `GET /api/audit/export?lang=es`: the whole current run as a JSON file to download.

The dashboard shows the latest 15 events in *Activity log* (*Registro de actuaciones*), polled every 3 s, with a *Download (JSON)* link.

## Service status

`GET /api/status/providers` reports each external service as `up`, `degraded`, `down`, `configured` (set up, never called, because checking would send a message) or `not_configured`, with a short reason in the request's language and the time of the last check.

| Service | Check |
|---|---|
| Deepfire | Token, then a one-feature read of the active clusters. 503 under load is *degraded*: live mode keeps its last answer |
| openrouteservice | A 100 m route. **A 403 "Quota exceeded" means the daily quota is spent: *degraded*, "quota spent: using the cached routes"**. Another 403 is a rejected key. Checked every 15 minutes, since a check counts against the quota while there is quota left |
| Overpass | The smallest query, on `OVERPASS_URL` and each mirror at once: all, some or none answer |
| SLNG | Reading the resident agent with the key (starts nothing) |
| Twilio SMS | Configured or not, and whether `HACKFIRE_CREW_PHONE` is set. No call |
| Vonage | Configured or not (video, and SMS for the link). No call |

The DGT traffic feed is not listed yet: when `providers/dgt.py` lands, add a `Provider` and its check in `PROVIDERS` in `backend/app/provider_status.py`, and its reasons in the `providers` section of the backend locales.

How it stays fast:

- The checks run in parallel in a small thread pool, each with a 4 s HTTP timeout.
- The endpoint waits for them at most 5 s. A check still running then keeps its last result, or reads "still checking", and stores its own when it finishes.
- Results are cached for 60 s (openrouteservice for 15 minutes), so the dashboard's poll once a minute costs at most one round of checks.
- The HTTP calls themselves live in `providers/` (`ping()` in `deepfire.py`, `routing.py`, `overpass.py`, `voice.py`).

The dashboard shows *Service status* (*Estado de los servicios*) at the bottom of the sidebar on a wide screen and at the end of the sheet on a phone: a dot in the status colours (green up, amber degraded, red down, grey not configured, hollow green configured), the state in words and the reason.
