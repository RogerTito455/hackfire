# SLNG

**Used for:** step 3 (the agent calls residents) and step 4 (crew notification, the coordinator's voice query). Slices 6–9 (#7, #8, #9, #10), latency numbers (#14).
**Status:** working. The resident agent (`voice/resident/`) is deployed on SLNG with its three API Request tools, and a real browser conversation changed a pin on the deployed dashboard (checkpoint 1, #7). The dashboard takes a resident's call in the browser through a web session; phone calls wait on a SIP trunk (#8)
**Owner:** Roger

## Access

https://app.slng.ai → Projects → new project → Generate key. Set `SLNG_API_KEY` in `.env`. Credits come from the SLNG mentors.

Every request sends `Authorization: Bearer $SLNG_API_KEY`.

| Host | For |
|---|---|
| `https://api.agents.slng.ai` | Agents, calls |
| `https://api.slng.ai` | Speech (STT, TTS) |
| `https://eu-west.api.slng.ai` (Germany), `https://eu-north.api.slng.ai` (Netherlands) | Regional speech hosts. There is no Spain region |

## Plan A: the Agent Builder (45-minute timebox, #7)

The Agent Builder can do everything slice 6 needs:

- **Call our five `/tools` endpoints** as "API Request" tools. The URL must be **HTTPS**, so the agent talks to the **deployed** backend (#2), or to a tunnel to your laptop. Auth: none, bearer, or HMAC through the Vault. Timeout 1–60 s. A tool must pass a test before it can be published and attached.
- **Attach the Deepfire MCP** over Streamable HTTP or SSE.
- **Think with an LLM SLNG serves**: for Spanish in its EU regions that means NVIDIA Nemotron Super 3 or Nano 3 ([finding](../findings/2026-09-19-slng-agent-llms-for-spanish.md)). The backend reaches the same model through SLNG's OpenAI-compatible Context Router (`providers/llm.py`). The team dropped Nebius from the stack on 2026-09-19.
- `tool_refs` and `mcp_refs` cannot be changed with `PATCH`; recreate or edit in the UI.

If by the end of the timebox it cannot call our tools, switch to plan B: our own STT → LLM → TTS pipeline on the SLNG gateway.

## Outbound calls (#8)

```
POST https://api.agents.slng.ai/v1/agents/{agent_id}/calls
{"phone_number": "+34…", "arguments": {"neighbor_id": "n02", "route": "…"}}
```

`arguments` fill the `{{variables}}` in the agent prompt: at most 32 keys, 1,024 characters per value. One call per request; 429 with `Retry-After` when rate-limited.

**In the app** (`backend/app/campaign.py`, `providers/voice.py`): once the coordinator approves a zone's order, **Call residents** dials every pending resident of the zone with the agent's call variables (`neighbor_id`, `resident_name`, `address`, `zone`, plus `fire_status` and `route` so it opens with the order); phones come from the registry and never leave the backend. Each call is polled (`GET …/calls/{call_id}`) until `call_ended_at` is set; a resident still pending then becomes `no_answer`, and one who told the agent something keeps it. Off until `HACKFIRE_PHONE_CALLS=1`, because no trunk exists yet, so dispatching and polling are **not yet run** against the live API (field names from the API reference; `call_id` or `id`, and `completed`/`failed` also end a call). Without it, `POST /api/neighbors/{id}/web-session` opens the same conversation in the browser (`POST …/web-sessions` returns a LiveKit URL and a five-minute token), which the dashboard joins with `livekit-client`; ran against the live API on 2026-09-19. Like a campaign call, it needs the zone's order approved.

**SLNG does not provide phone numbers.** Outbound calls need our own SIP trunk (for example Twilio Elastic SIP Trunking), set up in the admin-only Telephony section. Confirm with the mentors what they can lend us; the fallback is push-to-talk on the web. [Finding](../findings/2026-09-19-slng-bring-your-own-number.md).

## SMS for the crew (#9)

SLNG's "Send SMS" tool goes through Twilio only: it needs a Twilio Account SID, Auth Token and an SMS-capable number, and a successful test before publishing. Same dependency as the phone number. It is a tool an *agent* calls, not an API our backend can call.

What works: every new rescue creates a crew alert (`GET /api/alerts`) with the address, people, mobility and a link (`HACKFIRE_PUBLIC_URL/?rescue=<id>`) that opens the dashboard on the crew's route, shown on the dashboard. **With Twilio set up** (`TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_FROM_NUMBER` and `HACKFIRE_CREW_PHONE`), the backend also texts it to the crew through `providers/sms.py`, after answering the tool call so the agent never waits, and marks the alert "sent by SMS". A Twilio failure is logged and the alert stays on the dashboard. Not yet run against the live API.

## Spanish

| | Options |
|---|---|
| Speech to text | Soniox Speech AI RT v5, `soniox/speech-ai:rt-v5` (NL, DE; $0.0028/min); Deepgram Nova 3 (SLNG-hosted only in US, AU, IN) |
| Text to speech | Deepgram Aura 2, `deepgram/aura:2`, deployed in `eu` with 17 Spanish voices (`aura-2-nestor-es` is the agent's). Fish S2.1 Pro, `slng/fish/tts:s2.1-pro`, is deployed only in `nebius-eu-north1` and `ap-southeast-2` (`voiceai models --tts --json`, 2026-09-19) and failed in an `eu-north` agent with a `tts_error` |

For latency (#14), prefer the EU-hosted models: Soniox to listen, Fish to speak. Fish has **Castilian** voices meant for voice agents: Elena `566359628f6a4d5fabf902f6f64ecec1`, Marta `e8c4bf4a0a2d481991acf8bd1c25e2e0`, Sergio `ad2a0e367c664e1a88208e0311ef97ee`. The Aura Spanish voices do not say which accent they have.

The catalogue now lists Catalan too; see [the finding](../findings/2026-09-19-slng-lists-catalan.md). It stays out of scope.

### Quick check: text to speech in Spanish

The unified TTS endpoint is the fastest way to prove a key works and to pick a voice. Not yet run: nobody had an SLNG key in `.env` when this was written.

```bash
curl https://eu-west.api.slng.ai/v1/bridges/unmute/tts/slng/fish/tts:s2.1-pro \
  -H "Authorization: Bearer $SLNG_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"voice":"566359628f6a4d5fabf902f6f64ecec1","text":"Hola, soy el asistente de evacuación de HackFire."}' \
  --output hola.wav
```

The `model_variant` in the path must be one of the values in the spec (`slng/deepgram/aura:2-en`, `slng/fish/tts:s2.1-pro`, `deepgram/aura:2`, `soniox/tts-rt:v1`, …). Retype commands copied from web pages: a snippet pasted into the team chat carried invisible zero-width characters that break the shell.

## Unmute: the agent as files in the repo

[Unmute](https://unmute.ai) is SLNG's open-source compiler for voice agents. The agent lives in `agent.yaml` plus a Markdown prompt, and compiles to three targets: **SLNG** (hosted, `unmute deploy`), **Pipecat** or **LiveKit** (a Python project you run). The `/v1/bridges/unmute/...` endpoints above are SLNG's unified speech API, which you can call without the compiler.

**The resident agent is an Unmute package: [`voice/resident/`](../../voice/resident/).** How to validate, deploy and test it, the dashboard setup it needs, and every placeholder are in [`voice/README.md`](../../voice/README.md). It validates for the SLNG target with unmute 0.5.5; it has not been deployed yet.

What writing it taught us (v0.5.5, released 2026-09-18, so expect changes):

| | SLNG target | Pipecat target |
|---|---|---|
| Our `/tools` endpoints | **Refused as `webhook:` tools.** Create them as API Request tools in the SLNG dashboard first, then reference them by name as hosted tools (`slng: report_status`). `inject:` pins an argument to a call variable | Allowed as `webhook:` tools. Hosted tools only compile with a mirror fetched by `unmute pull` |
| The LLM | One SLNG serves, named in `agent.yaml` without a `provider:` (`bedrock-mantle/nvidia.nemotron-super-3-120b:latest`) | `provider: slng` through the Context Router, reading `SLNG_API_KEY` |
| Region | `deployment_region` in `targets.yaml`: one of `eu-west`, `eu-north`, … | `params.world_part` on SLNG speech models picks the gateway |
| Turn detection | SLNG's own; a `turn:` model is refused | A `turn:` model is required |
| Deepfire MCP | Validates with an explicit `mcp.tools` list, once the server is registered in the SLNG organisation. Left out of the resident agent; see `voice/README.md` | Allowed |
| Outbound calls | Not declared in the package; a trunk attached to the agent in the dashboard survives pushes. `unmute deploy --call <E.164>` rings a phone | Twilio, deployed to Pipecat Cloud |
| Local test | None. The dashboard's Test agent panel cannot pass call variables, so the package carries test defaults | `unmute dev --var name=value` opens a browser voice loop (needs `uv`) |

**One package cannot serve both targets.** The `turn:` model Pipecat requires is refused on SLNG, and a `targets.yaml` override can only replace an entry that already exists. A Pipecat fallback is a second package; `voice/README.md` lists what it needs, and that recipe validated.

The route that keeps the 45-minute timebox honest:

1. Create `get_evacuation_route` and `report_status` (and `get_fire_status`, published but no longer attached to the resident agent) as API Request tools, pointing at the deployed backend (#2). The coordinator agent (#10) will need the other two.
2. Name an LLM SLNG serves in `voice/resident/agent.yaml`.
3. `unmute deploy` to the SLNG target, and check the agent from the SLNG dashboard's browser test. That is checkpoint 1 (#7).
4. If the SLNG target fights back when the timebox runs out, build the Pipecat variant. `unmute dev` gives a browser voice loop that doubles as the push-to-talk fallback. It still beats hand-writing an STT → LLM → TTS pipeline.

Install: take the Linux archive and `checksums.txt` from https://github.com/slng-ai/unmute/releases and check the archive before extracting, or `go install github.com/slng-ai/unmute@latest` (Go 1.26+). Its Claude Code skills (`unmute`, `unmute-deploy`, `unmute-manifest`) are installed in the repo with `unmute skill install`; the text lives in `.agents/skills/` and `.claude/skills/` points to it.

## Latency numbers (#14)

SLNG keeps a report of every finished call. `pnpm voice:latency` reads them (only reads) and prints the median and worst case for the slide and how they were computed; `--since <ISO time>` and `--all` change which calls count. It needs the `SLNG_API_KEY` **of the project that holds the agent**: a key from another project authenticates but lists no agents.

- **Which calls.** By default, those that started after the agent's `updated_at`, the moment its current version was deployed. Any edit or redeploy moves that moment and leaves earlier calls out, so **measure once the agent is frozen** and say the deployment time next to the numbers. The script prints it.
- **How a turn is timed.** From the resident's `stopped_speaking_at` to the agent's next `started_speaking_at`. Not SLNG's `e2e_latency`: that field is only on messages where the agent answers directly. When it calls a tool first (the slow turns) the message that finally speaks has none, so a median over it would leave them out. Where SLNG does give one it equals this figure (checked: 0.000 s apart). The code is `backend/app/latency.py`, with tests on the shapes seen in a real report: a tool-call turn, a resident message that continues a turn, an agent already speaking, an interrupted reply, null timings.
- **Where it lives.** `GET /v1/agents/{id}/calls` answers `{items, meta}`, 20 to a page (`?page=`); `GET …/calls/{call_id}` carries `livekit_session_report.chat_history.items` (messages with `metrics`, `function_call`, `function_call_output`). The report only exists once the call has ended.
- **What makes a bad call.** A browser session left open stops at 300 s ("web session max duration reached") with no conversation in it; hang up yourself. A call that has just ended can lack its report for a minute: the script says so and leaves it out instead of counting it as zero turns. The greeting has no resident turn before it, so it is not a turn.
- **What to report.** At least ten turns (SLNG's brief), the median and the worst case, the deployment time of the agent version, and the split between turns answered directly and turns with a tool (the latter are slower). Put them in a finding with the calls used ([template](../findings/README.md)) and hand the two numbers to the slide (#15).

## CLI and SDKs

- **`voiceai` CLI** (source: https://github.com/slng-ai/sdks): `whoami`, `tts`, `stt`, `agents {list,create,push}`, `agents calls dispatch`, `trunks list`, `mcp list`. Handy for scripting the voice track and for checking what trunk we have. The install script `https://docs.slng.ai/install.sh` returned 404 on 2026-09-19; take `voiceai-linux-x64` from the latest `cli-v*` release of `slng-ai/sdks` instead (see [voice/README.md](../../voice/README.md#commands)). It reads `VOICEAI_API_KEY`, not `SLNG_API_KEY`, so export both.
- **Python SDK** `voiceai-sdk`, if the backend ever needs more than `httpx`: `uv add voiceai-sdk` inside `backend/`. It defaults to `SLNG_API_KEY`.

`slng-ai/sdks` is not an MCP server; it is the source of the CLI and SDKs.

## In Claude Code

- The `slng-docs` MCP server in `.mcp.json` searches the SLNG docs. It is not documented by SLNG, but it answered on 2026-09-19. The same docs are at https://docs.slng.ai/llms-full.txt.
- The `agents` and `agent-prompt` skills from [slng-ai/skills](https://github.com/slng-ai/skills) are installed in `.claude/skills/`: `agent-prompt` drafts the greeting, system prompt, variables and tools for the Agent Builder; `agents` creates agents and dispatches calls through the API. They suggest `npm install -g` and `pip install`; in this repo use the install script and `uv add` instead.

## Sources

- https://docs.slng.ai/llms.txt · https://docs.slng.ai/llms-full.txt
- Authentication: https://docs.slng.ai/api-reference/authentication.md
- Telephony: https://docs.slng.ai/guides/agents/telephony/overview.md · /outbound.md · /dispatch-calls.md
- Tools and MCP: https://docs.slng.ai/guides/agents/tools-and-mcp/api-request-tool.md · /connect-with-mcp.md · /send-sms-tool.md
- Bring your own key: https://docs.slng.ai/guides/models/bring-your-own-key.md
- Models by language: https://docs.slng.ai/models/catalog/by-language.md
