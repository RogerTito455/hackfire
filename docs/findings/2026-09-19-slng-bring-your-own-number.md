# SLNG does not provide phone numbers, and its tools need HTTPS

**Date:** 2026-09-19 · **Area:** SLNG, slices 6–9 (#7, #8, #9)

## What happened

Reading the SLNG docs before building the voice track turned up two dependencies the plan did not list.

1. **Phone numbers.** SLNG's telephony guide says you bring your own phone numbers; they do not come from SLNG. Outbound calls need a SIP trunk, for example Twilio Elastic SIP Trunking, configured in the admin-only Telephony section. SMS goes through Twilio only (Account SID, Auth Token, an SMS-capable number).
2. **HTTPS tools.** An Agent Builder "API Request" tool must point at an HTTPS URL. `http://localhost:8000/tools/...` will not work.

Not verified against the live service yet.

## What we do about it

1. Ask the SLNG mentors exactly what they can provide: a number on their trunk, Twilio credentials, or nothing. Issue #1 already expects "a phone number, or a decision to fall back to web push-to-talk"; this finding makes the fallback more likely.
2. Deploy the backend early (#2) so the agent's tools have an HTTPS URL. While developing, a tunnel to the laptop works too.
3. The crew notification (#9) has the same Twilio dependency. If there is no SMS, show the notification on the dashboard and say so in the pitch.

## Sources

- https://docs.slng.ai/guides/agents/telephony/overview.md
- https://docs.slng.ai/guides/agents/telephony/outbound.md
- https://docs.slng.ai/guides/agents/tools-and-mcp/api-request-tool.md
- https://docs.slng.ai/guides/agents/tools-and-mcp/send-sms-tool.md
