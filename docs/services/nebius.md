# Nebius Token Factory

**Used for:** the agent's reasoning and the structured extraction that turns what a resident says into `report_status` (step 3 → step 4). Slice 6 (#7).
**Status:** thin client written (`backend/app/providers/llm.py`), not yet run
**Owner:** Roger

## Access

https://tokenfactory.nebius.com → create an API key. Set in `.env`:

```
NEBIUS_API_KEY=...
NEBIUS_BASE_URL=https://api.tokenfactory.nebius.com/v1
NEBIUS_MODEL=<model id, see below>
```

**Budget:** new accounts get $1 of trial credit, valid for 30 days, and billing setup needs a bank card. Ask the Nebius mentors for credits before load-testing.

## In the app

The API is OpenAI-compatible: `POST /v1/chat/completions` with `Authorization: Bearer $NEBIUS_API_KEY`.

- **Tool calling:** OpenAI-format `tools`, `tool_choice` set to `auto` or a named function.
- **Structured output:** `response_format` of `json_schema` or `json_object`, on models tagged "JSON mode" on their model card. Use `json_schema` with the `ReportStatusRequest` shape for triage, so the model cannot invent a status.
- **Picking a model:** the docs do not list which models support tool calling. List what is available, then check the model cards:

```bash
curl -s "https://api.tokenfactory.nebius.com/v1/models?verbose=true" \
  -H "Authorization: Bearer $NEBIUS_API_KEY"
```

(Not yet run.) `verbose=true` adds context length, pricing and per-model limits. Models were deprecated in June and August 2026, so do not copy a model id from an old tutorial.

For a phone call, latency matters more than size: prefer a fast instruct model that has both the tool-calling and JSON tags.

## Inside SLNG

If the SLNG Agent Builder routes to Nebius, it is configured there (bring-your-own-key: model id, key, endpoint URL) and our backend never sees the conversation, only the tool calls. See [SLNG](slng.md).

## In Claude Code

The `nebius-docs` MCP server in `.mcp.json` searches the Token Factory docs. It is undocumented, but it answered on 2026-09-19.

## Gotchas

- Rate limits are dynamic and return 429; they can grow to 20× the base with usage.

## Sources

- Quickstart: https://docs.tokenfactory.nebius.com/quickstart
- Models: https://docs.tokenfactory.nebius.com/api-reference/examples/list-of-models
- Function calling: https://docs.tokenfactory.nebius.com/ai-models-inference/function-calling
- JSON mode: https://docs.tokenfactory.nebius.com/ai-models-inference/json
- Rate limits: https://docs.tokenfactory.nebius.com/ai-models-inference/rate-limits
