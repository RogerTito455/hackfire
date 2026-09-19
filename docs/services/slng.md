# SLNG

**Used for:** step 3 (the agent calls residents) and step 4 (crew notification, the coordinator's voice query). Slices 6–9 (#7, #8, #9, #10), latency numbers (#14).
**Status:** not started. `backend/app/providers/voice.py` is a stub
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
- **Use Nebius as the LLM** through bring-your-own-key ("LLM providers" tab): model id, `NEBIUS_API_KEY`, endpoint `https://api.tokenfactory.nebius.com/v1`. Nebius is not named in SLNG's docs; it should work as an OpenAI-compatible endpoint, but that is not yet tested.
- `tool_refs` and `mcp_refs` cannot be changed with `PATCH`; recreate or edit in the UI.

If by the end of the timebox it cannot call our tools or route to Nebius, switch to plan B: our own STT → LLM → TTS pipeline on the SLNG gateway.

## Outbound calls (#8)

```
POST https://api.agents.slng.ai/v1/agents/{agent_id}/calls
{"phone_number": "+34…", "arguments": {"neighbor_id": "n02", "route": "…"}}
```

`arguments` fill the `{{variables}}` in the agent prompt: at most 32 keys, 1,024 characters per value. One call per request; 429 with `Retry-After` when rate-limited.

**SLNG does not provide phone numbers.** Outbound calls need our own SIP trunk (for example Twilio Elastic SIP Trunking), set up in the admin-only Telephony section. Confirm with the mentors what they can lend us; the fallback is push-to-talk on the web. [Finding](../findings/2026-09-19-slng-bring-your-own-number.md).

## SMS for the crew (#9)

SLNG's "Send SMS" tool goes through Twilio only: it needs a Twilio Account SID, Auth Token and an SMS-capable number, and a successful test before publishing. Same dependency as the phone number.

## Spanish

| | Options |
|---|---|
| Speech to text | Soniox Speech AI RT v5, `soniox/speech-ai:rt-v5` (NL, DE; $0.0028/min); Deepgram Nova 3 (SLNG-hosted only in US, AU, IN) |
| Text to speech | Fish S2.1 Pro, `slng/fish/tts:s2.1-pro` (SLNG-hosted in NL, DE); Deepgram Aura 2 Spanish voices (`aura-2-alvaro-es`, `aura-2-celeste-es`…), but SLNG-hosted only in the US |

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

What it would mean for us (checked against v0.5.5, released 2026-09-18, so expect changes):

| | SLNG target | Pipecat target |
|---|---|---|
| Our five `/tools` endpoints | **Refused as `webhook:` tools.** Create them as API Request tools in the SLNG dashboard first, then reference them by name as hosted tools | Allowed as `webhook:` tools |
| Nebius as the LLM | Through SLNG's router (`openai-compat` provider) | `openai-compat` endpoint |
| Deepfire MCP | Allowed, with an explicit `mcp.tools` list | Allowed |
| Outbound calls | Not declared in the package; `unmute deploy` attaches an existing trunk | Twilio, deployed to Pipecat Cloud |
| Local test | None (`unmute dev` does not exist for SLNG) | `unmute dev` opens a browser voice loop (needs `uv`) |

**Our take:** the team counts Unmute as a plus for the SLNG challenge, so the agent should end up as an Unmute package in the repo rather than only as clicks in the Agent Builder. A route that keeps the 45-minute timebox honest:

1. Create the five `/tools` endpoints as API Request tools in the SLNG dashboard, pointing at the deployed backend (#2). Both routes below need them.
2. Write the package: `agent.yaml` with the prompt, Soniox to listen, Fish to speak, Nebius through `openai-compat` to think, our five tools as hosted tools referenced by name, and the Deepfire MCP with an explicit tool list.
3. `unmute deploy` to the SLNG target, and check the agent from the SLNG dashboard's browser test. That is checkpoint 1 (#7).
4. If the SLNG target fights back when the timebox runs out, compile the same package for **Pipecat** instead. There, webhook tools are allowed and `unmute dev` gives a browser voice loop that doubles as the push-to-talk fallback. It still beats hand-writing an STT → LLM → TTS pipeline.

To check before step 2: the docs suggest hosted tools also compile for Pipecat and LiveKit (they refuse only hosted tools that declare Python dependencies). If so, one package serves both targets unchanged. Where the package lives in the repo is Roger's call; add it to the layout in CLAUDE.md when it lands.

Install: take the Linux archive from https://github.com/slng-ai/unmute/releases, or `go install github.com/slng-ai/unmute@latest` (Go 1.26+). `unmute skill install` then adds its Claude Code skill; only do that if we adopt it.

## CLI and SDKs

- **`voiceai` CLI** (source: https://github.com/slng-ai/sdks): `whoami`, `tts`, `stt`, `agents {list,create,push}`, `agents calls dispatch`, `trunks list`, `mcp list`. Handy for scripting the voice track and for checking what trunk we have. Install with `curl -fsSL https://docs.slng.ai/install.sh | sh`. It reads `VOICEAI_API_KEY`, not `SLNG_API_KEY`, so export both.
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
