# SLNG passes a tool's arguments to our backend unchecked

**Date:** 2026-09-19 · **Area:** SLNG, tool contract

## What happened

Before writing the contract test for `report_status`, we pointed a throwaway API Request tool with the same parameter schema at `https://httpbin.org/anything` and test-ran it, to see the exact request SLNG sends. (The tool was deleted afterwards.)

- The body is the model's arguments as raw JSON, with no envelope: `{"neighbor_id":"n01","status":"evacuating"}`. `Content-Type: application/json`, `User-Agent: python-httpx`.
- Optional parameters the model leaves out are omitted, not sent as `null`.
- **Types are not checked.** `"people": null`, `"mobility": ""` and `"people": "3"` (a number as text) all reach the endpoint exactly as written, although the schema says `integer`.
- With `strict: true`, an argument the schema does not declare is refused before any request is sent: `undeclared arguments rejected (strict): extra`.

## Why

Not verified. SLNG's `strict` option appears to check argument names only, not types.

## What we do about it

For #7:

- `ReportStatusRequest` reads a count sent as text, and treats one it cannot read (`"unos tres"`) as unknown instead of answering 422. A rejected `report_status` would leave the pin unchanged in the middle of an emergency call. Tests in `backend/tests/test_tools.py`.
- The three tools are created with `strict: true`.

## Sources

- https://docs.slng.ai/guides/agents/tools-and-mcp/api-request-tool.md
- https://docs.slng.ai/api-reference/agents-resources/tools.md
