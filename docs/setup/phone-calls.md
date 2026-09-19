# Phone calls through a Vonage SIP trunk

**Status:** not yet run. Written on 2026-09-19 from the SLNG and Vonage docs, before any call went through the trunk. Anything marked *not documented* is a gap in the vendors' docs: the first test call settles it, so update this page afterwards.
**Issue:** #8

SLNG supplies no phone numbers ([finding](../findings/2026-09-19-slng-bring-your-own-number.md)). The team has a US Vonage number with voice. This page connects it to the resident agent over SIP so the agent can ring real phones: first one team phone from SLNG's test panel, then a call campaign from the dashboard. Everything is set by hand in two dashboards; the repo only gets a switch.

```
backend: POST /api/campaigns/{zone}
   │  POST https://api.agents.slng.ai/v1/agents/{id}/calls   (phone_number + call variables)
   ▼
SLNG resident agent (hackfire-resident-slng, eu-north)
   │  outbound connection: SIP, digest auth, caller ID = the Vonage number
   ▼
Vonage SIP trunk  <domain>.sip-eu.vonage.com
   │  phone network
   ▼
a team member's phone (+34…)
```

Whichever backend dispatches the call, the agent's tools (`report_status`, `get_evacuation_route`) call the **Railway** backend, because that is the URL they were published with ([voice/README.md](../../voice/README.md#from-package-to-phone-call-in-order)).

## Values that move between dashboards

Nothing here goes into `.env` or git: nothing in the repo reads them. Keep the two secrets in a password manager and share them only privately.

| Value | Created in | Pasted into | Secret |
|---|---|---|---|
| Trunk domain, e.g. `hackfire-slng` → termination host `hackfire-slng.sip-eu.vonage.com` | Vonage, SIP trunk | SLNG outbound connection, **Termination host** | No |
| Trunk **User Key** (the SIP username) | Vonage, trunk **Outbound Calling → Authentication** | SLNG, **Auth username** | Yes |
| Trunk **Secret** (the SIP password) | Same | SLNG, **Auth password** | Yes |
| The Vonage number, in E.164 with `+` | Vonage, **Numbers → Your numbers** | SLNG, **Caller ID pool** | No, but keep it out of the repo like every phone number |
| SLNG connection id (optional, for the API) | SLNG, after the connection is created | `PATCH /v1/agents/{id}` as `sip_outbound_trunk_id` | No |
| Optional inbound: SLNG **Forwarding target** | SLNG, inbound connection → **View setup** | Vonage trunk, inbound **SIP URIs** | Treat as private (not documented) |

## Before you start

- **A Vonage account out of trial, with credit.** A trial account can place voice calls only to the account's own registered number ([Vonage support](https://api.support.vonage.com/hc/en-us/articles/212554438-What-are-the-limitations-of-a-trial-account); the page refuses automated reads, so this is from its search summary). Upgrading means adding a payment method; check the balance too.
- **Spain allowed for Voice in Fraud Defender.** Dashboard → **Fraud Defender** → *Protections* → **Countries** → **Review**: countries can be toggled per channel, and **Traffic Rules** (allow or block by prefix) win over it ([Vonage support](https://api.support.vonage.com/hc/en-us/articles/10283720577052-How-to-allow-my-SMS-or-Voice-Traffic-to-only-some-countries-using-Fraud-Defender), same caveat). Whether Spain is on by default is not documented.
- **Admin rights in the SLNG organisation.** Creating a connection happens only in the dashboard's **Telephony** section, which is admin only; the public API cannot create one ([SLNG](https://docs.slng.ai/guides/agents/telephony/overview.md)).
- **`SLNG_API_KEY` in `.env`**, for the checks below.
- **The registry with the team's own phones, in E.164 with `+`** (`+34…`), because SLNG's dispatch takes an E.164 number ([SLNG API](https://docs.slng.ai/api-reference/calls/dispatch-call.md)). Locally that is `data/neighbors.local.json`; on Railway, `HACKFIRE_NEIGHBORS_JSON` ([Deployment](deployment.md#the-real-registry)).
- A phone you can answer.

## 1. Vonage: a SIP trunk

The current way to send calls from your own SIP equipment through Vonage is a trunk made in the **SIP Dashboard** ([Vonage](https://developer.vonage.com/en/sip/sip-dashboard)).

1. Vonage API Dashboard → **Build → Voice → SIP**. The first time, a **SIP Trunking wizard** opens: **Get Started**. Later trunks: **SIP → + Create new**.
2. **Domain name:** unique, 5 to 32 characters, letters, digits or dashes only. For example `hackfire-slng`.
3. **Outbound Calling → Add Authentication → User Key and Secret.** Vonage creates a username and password for digest authentication; keep them or edit them. The password must be 12 to 64 characters with at least one digit, one lower-case and one upper-case letter. That also meets SLNG's upper-case rule ([SLNG](https://docs.slng.ai/guides/agents/telephony/outbound.md)).
   - Do **not** rely on the **Access Control List** (IP allow-list) alone: SLNG does not publish the addresses its SIP traffic comes from (not documented). Digest credentials are enough; Vonage accepts either or both ([Vonage](https://developer.vonage.com/en/sip/technical-details)).
4. **Termination URI:** the trunk page lists one per region: `<domain>.sip-us.vonage.com` (AMER), `<domain>.sip-eu.vonage.com` (EMEA), `<domain>.sip-ap.vonage.com` (APAC) ([Synthflow's Vonage guide](https://docs.synthflow.ai/sip-with-vonage), [Vonage](https://developer.vonage.com/en/sip/sip-dashboard)). Copy the **EMEA** one: the agent runs in the Netherlands and the phones are in Spain. The page shows the exact host; copy it rather than typing it.
5. **Caller ID.** Vonage accepts as caller ID "a Vonage Number associated with your account with no limitation on outbound calling"; any other number "will result in call blocking" ([Vonage](https://developer.vonage.com/en/voice/voice-api/concepts/numbers)). The US number is in the account, so this holds.
6. **Link the number to the trunk (recommended).** **Inbound Calling → Link Numbers** attaches it ([Vonage](https://developer.vonage.com/en/sip/sip-dashboard)). The docs describe linking for inbound calls; whether outbound caller ID needs it is not documented. Linking changes where calls *to* the number go, and that number is unused today.

Vonage's side of the protocol ([Vonage](https://developer.vonage.com/en/sip/technical-details)):

| | Vonage accepts |
|---|---|
| Transport | UDP or TCP on 5060, TLS 1.2 on 5061 |
| Codecs | PCMA (G.711a), PCMU (G.711u), iLBC, G.729, G.722, Speex16 |
| Media | RTP or SRTP (`AES_CM_128_HMAC_SHA1_80`) |
| DTMF | Out of band, RFC 4733 |
| Numbers | Destination "must be in E.164 format"; caller ID in the `From` header, or in `P-Asserted-Identity` when set ([numbers](https://developer.vonage.com/en/voice/voice-api/concepts/numbers)) |

**The plus sign.** Vonage's docs write E.164 *without* the leading `+` ("Omit both a leading `+` and the international access code"; example `From: <447700900000@yourcompany.com>`), while SLNG asks for caller IDs and destinations *with* it (`+15551234567`). Whether Vonage accepts a `+` in the `From` user or the request URI is not documented. Start with `+`, SLNG's format; see *Troubleshooting* if the call is refused.

**Fallback, legacy Vonage SIP.** Older Vonage guides send calls to `sip.nexmo.com` with the account's **API key** as SIP username and **API secret** as password, and the Vonage number as the from-user; codec `alaw` outside the US ([Vonage, legacy](https://developer.vonage.com/en/sip/configure/asterisk-legacy)). The API key and secret are under the Dashboard's [account settings](https://dashboard.nexmo.com/settings) ([Vonage](https://developer.vonage.com/en/getting-started/concepts/authentication)). Use it only if the trunk above cannot be made; whether it accepts SLNG's connection is not documented.

## 2. SLNG: an outbound connection on the resident agent

From SLNG's guide for any carrier other than Twilio ([SLNG](https://docs.slng.ai/guides/agents/telephony/outbound.md)).

1. Dashboard sidebar → **Telephony** → **Outbound** tab → **Add connection** → **Manual**.
2. Fill in:

   | Field | Value |
   |---|---|
   | **Connection name** | `hackfire-vonage-outbound` |
   | **Termination host** | The EMEA termination URI from Vonage, host only, as in SLNG's example `wayne.pstn.twilio.com` |
   | **Caller ID pool (rotates)** | The Vonage number in E.164 with `+`. The caller ID always comes from this pool, never from the dispatch request |
   | **Transport** | **Auto**. If calls fail at the SIP level, try **UDP**. **TLS** makes Vonage expect port 5061 |

3. **Auth username** = the trunk's User Key; **Auth password** = the trunk's Secret. In Manual mode there is no checklist: Vonage must simply accept these credentials.
4. **Create connection.** It starts `pending` and becomes `active`; `error` shows the reason. It cannot be attached until it is active.
5. **Attach it to the resident agent.** Open the project `hackfire-resident-slng` → its **Telephony** section → **Outbound calls** → pick `hackfire-vonage-outbound`. Or through the API, which `unmute` cannot do:

   ```bash
   set -a; . ./.env; set +a     # from the repo root; prints nothing
   A=${SLNG_RESIDENT_AGENT_ID:-0f035ccc-10d8-4de8-8142-abf4dc484fd8}
   curl -s https://api.agents.slng.ai/v1/agents/$A/sip-trunk-options \
     -H "Authorization: Bearer $SLNG_API_KEY"
   # outbound[]: the connection with "status":"active", "selectable":true, "unavailable_reason":null
   curl -s -X PATCH https://api.agents.slng.ai/v1/agents/$A \
     -H "Authorization: Bearer $SLNG_API_KEY" -H "Content-Type: application/json" \
     -d '{"sip_outbound_trunk_id":"<connection id>"}'
   ```

   `voiceai trunks list --direction outbound` shows the same connections ([`agents` skill](../../.claude/skills/agents/references/org-resources.md)).

**Region.** The resident agent runs in `eu-north` (`voice/resident/targets.yaml`). A connection is only attachable to agents in its region; otherwise the picker marks it **(Unavailable)** with `different_livekit_project` ([SLNG](https://docs.slng.ai/guides/agents/telephony/overview.md)). How a connection's region is chosen is not documented: the wizard has no region field. If it comes out unavailable, ask the SLNG mentors. Do not move the agent to another region: its Spanish models were chosen for eu-north ([finding](../findings/2026-09-19-slng-agent-llms-for-spanish.md)).

**`outbound_greeting`: leave it empty.** It is optional: a directional greeting that replaces `greeting` on calls the agent places, and the agent refuses to save one unless a connection is attached ([SLNG](https://docs.slng.ai/guides/agents/telephony/overview.md), [features](https://docs.slng.ai/concepts/agents/features.md)). The resident agent's greeting is already an outbound one ("Hola, buenas. ¿Hablo con {{resident_name}}?", `voice/resident/agent.yaml`).

**Deploys keep the connection.** `unmute deploy` leaves `sip_outbound_trunk_id` and `outbound_greeting` alone (observed on four pushes, `.agents/skills/unmute-deploy/SKILL.md`). `pnpm voice:goodbye` reads the whole agent and PUTs it back, and `sip_outbound_trunk_id` is not among the fields it drops (`backend/app/providers/voice.py`), so it survives too; not yet run with a connection attached. Check with `sip-trunk-options` (`"is_current": true`) after a deploy.

## 3. First call: SLNG's test panel

This tests Vonage and SLNG alone, before the backend is involved.

1. Project `hackfire-resident-slng` → **Test agent** → **Channel: Outbound call**. If the panel says telephony setup is needed, the connection is not attached.
2. **Number to call:** your own phone in E.164 (`+34…`) → **Start call** ([SLNG](https://docs.slng.ai/guides/agents/telephony/dispatch-calls.md)).
3. What to expect:
   - The phone rings with the Vonage number as caller ID (an international `+1` number on a Spanish phone). Whether the caller ID survives the international route intact is not documented.
   - When you answer, the agent speaks first. The panel cannot pass call variables, so it uses the **test defaults**: it greets "Resident 01" and talks about sample resident `n01` ([voice/README.md](../../voice/README.md#placeholders-and-open-questions)).
   - If you answer the three questions, `report_status` changes **n01's** pin on the Railway dashboard. `POST $B/api/reset` afterwards.
   - A voicemail that picks up gets the whole script: the agent has no answering-machine detection attached.
4. Read the result in **Observe → Calls** ([SLNG](https://docs.slng.ai/guides/agents/debug-a-call.md)): **Direction** (phone, not Web), **Status**, **Duration**. Open the call: **Metadata** has **End reason** and **Error message**, **Events** the failing step, **Tools** each tool's **Outcome** and **HTTP** status, **Transcript** the conversation. The same record comes from `GET /v1/agents/{agent}/calls/{call_id}` (`status`, `call_ended_at`, `call_end_reason`, `error_message`) ([SLNG API](https://docs.slng.ai/api-reference/calls/get-call.md)) or `voiceai agents calls get <agent> <call> --json`.

## 4. The repo: turn phones on

`HACKFIRE_PHONE_CALLS=1` switches the call campaign from "no phone line" to dialling, as long as `SLNG_API_KEY` is set too (`phone_calls_configured()` in `backend/app/providers/voice.py`). `SLNG_RESIDENT_AGENT_ID` defaults to the deployed resident agent.

**On Railway (use this for the test).** Service → **Variables**: `HACKFIRE_PHONE_CALLS` = `1`, plus `HACKFIRE_NEIGHBORS_JSON` with the team's registry if it is not there yet ([Deployment](deployment.md#the-real-registry)). Changing a variable redeploys and wipes the triage state. Then:

```bash
B=https://frontend-production-ae2c.up.railway.app
curl -s $B/api/voice          # "phone_calls": true
curl -s $B/api/neighbors      # the residents, and no phone number anywhere
```

**Locally.** `HACKFIRE_PHONE_CALLS=1` in `.env`, then `pnpm dev:api` and `pnpm dev:web`; `data/neighbors.local.json` is used when it exists. The phone rings, but the agent reports to Railway, not to your laptop: the local dashboard never sees the answer and marks the resident *No answer* when the call ends. Railway must also know the same resident id, or `report_status` answers 404 (visible in the call's **Tools** tab). So a local run only proves that dialling works.

## 5. Second call: from the dashboard

A campaign rings **every** resident of the zone who is still *Not called yet* and has no call in progress (`backend/app/campaign.py`). To ring one phone only, choose a zone where that is the only pending resident, or first give the others a status by hand (their panel → **Voice not working? Type the answer** → **Set the status by hand**), and **Reset demo** afterwards.

1. **Simulate the calls** must be off: while it is on, the campaign answers 409 "Turn off the call simulation before calling residents", so real phones never ring for a simulated workflow.
2. **Evacuation orders** → the zone → pick the order → **Approve order**.
3. **Call residents**. The panel says "Calling 1 resident; an unanswered call turns into No answer." If it says "SLNG refused the call to 1 resident: marked No answer.", SLNG did not place the call: see the backend log line `SLNG refused the call to <id>: <error>`.
4. Answer as the resident. The agent greets you by the registry name and gives the approved order and route. When it records the answer, the pin changes within about two seconds. Hang up without an answer and the resident becomes *No answer* once SLNG reports the call ended (the backend asks every 5 s).

The same through the API:

```bash
curl -s $B/api/safe-points                     # destination ids
curl -s -X POST $B/api/orders/<zone> -H 'Content-Type: application/json' \
  -d '{"action":"evacuate","destination_id":"<safe point id>"}'
curl -s -X POST $B/api/campaigns/<zone>        # [{"neighbor_id":"…","call_id":"…"}]; call_id null = refused
```

Not yet run: dispatching and polling follow the API reference (`call_id`, `call_ended_at`, `status`) and have never met a live trunk.

## Troubleshooting

| Symptom | Where it shows | Likely cause | What to do |
|---|---|---|---|
| Connection stuck `pending`, or `error` | SLNG **Telephony** | Provisioning; wrong host | Open it for the reason; re-copy the host from Vonage |
| **(Unavailable)** `different_livekit_project` | Agent's connection picker, `sip-trunk-options` | Connection and agent in different regions | Ask the SLNG mentors how to make it in eu-north (not documented) |
| **(Unavailable)** `not_synced` / `inactive` | Same | Provisioning not finished / failed | Wait and reload / open the connection for the error |
| Test panel: telephony setup needed | Test agent | No connection attached | Section 2, step 5 |
| 401 or 407 from Vonage | Call **Metadata → Error message**, **Events** | Digest credentials refused | Re-enter the User Key and Secret on both sides together; check **Add Authentication** was saved on the trunk |
| 403 from Vonage | Same | Caller ID not accepted (number not in the account, or its format), or destination blocked (trial account, Fraud Defender country or Traffic Rule, no credit) | Check each; then try the caller ID without `+` (`1…`), if SLNG's form accepts it (not documented) |
| 404 or 484 from Vonage | Same | Destination format | Not documented whether Vonage takes `+34…`; SLNG requires E.164 in the dispatch |
| Rings, but silence or one-way audio | The call | Codec, SRTP or NAT | Set Transport to UDP. Vonage takes G.711; SLNG's codecs are not documented. SRTP is not needed: Vonage accepts plain RTP |
| Caller ID hidden or odd on the Spanish phone | The phone | The international route | Not documented. Spain blocks calls from abroad that show a **Spanish** number (Orden TDF/149/2025, art. 5.1); the US number is not affected. Never put a Spanish number in the pool without checking where Vonage hands the call over |
| "No phone line: take each resident's call from their panel." | Evacuation orders | `HACKFIRE_PHONE_CALLS` is not `1`, or `SLNG_API_KEY` is missing | Set them; restart or redeploy; `curl $B/api/voice` |
| "SLNG refused the call…" | Evacuation orders, backend log | Dispatch failed: 400/422 (no connection, bad number), 402 (SLNG credit), 429 (rate limit; the campaign does not retry) | Read the log line and fix the cause. The resident is now *No answer*, so the campaign skips them until **Reset demo** |
| Call fine, pin unchanged, resident *No answer* | Dashboard, call **Tools** tab | Dispatched from a laptop, or the resident id is unknown on Railway (404) | Run the campaign on Railway with the same registry |

## Costs

- **The Vonage number:** €0.93 a month, renewing on the 19th (the owner's purchase, 2026-09-19).
- **Vonage per minute to a Spanish mobile:** not documented here; vonage.com's pricing pages refuse automated reads. The Pricing API returns the price per Spanish network, mobile and landline, with the account's API key and secret ([Vonage](https://developer.vonage.com/en/api/pricing)): `curl -s -u "$VONAGE_API_KEY:$VONAGE_API_SECRET" "https://rest.nexmo.com/account/get-pricing/outbound/voice?country=ES"`, with both exported in your shell for that one command (they are not repo variables). Whether trunk minutes cost the same as Voice API minutes is not documented.
- **SLNG:** each call uses the credits from the mentors; **Usage** records usage and costs per project ([SLNG](https://docs.slng.ai/concepts/agents/features.md)). A 402 on dispatch means payment required ([SLNG API](https://docs.slng.ai/api-reference/calls/dispatch-call.md)).

## Optional: calls to the number reach an agent

Not needed for the test. On SLNG: **Telephony → Inbound → Add connection → Manual**, add the Vonage number, create it, and copy the **Forwarding target** from **View setup** ([SLNG](https://docs.slng.ai/guides/agents/telephony/inbound.md)). On Vonage: the trunk's inbound section, pick the region, add that target under **SIP URIs** (priority 0 is highest; timeout 2,000–20,000 ms, default 5,000), and link the number ([Vonage](https://developer.vonage.com/en/sip/sip-dashboard)). An inbound connection belongs to one agent only; the coordinator agent is the one a firefighter would call ([voice/README.md](../../voice/README.md#the-coordinator-agent-coordinator-10)). A required call variable needs a default for inbound calls, or SLNG refuses to attach the trunk (`.agents/skills/unmute-deploy/references/slng-push.md`).

The alternative is a Vonage Voice application whose answer URL returns an NCCO `connect` to `{"type":"sip","uri":"sip:…"}` with a Vonage number as `from` ([Vonage](https://developer.vonage.com/en/voice/voice-api/ncco-reference)). It needs an endpoint in our backend, so it is not worth it for the hackathon.

## Still unverified

- Whether Vonage accepts a `+` in the caller ID and in the destination, and whether SLNG accepts a caller ID without it.
- How SLNG chooses a connection's region, and whether a new one is attachable to the eu-north agent.
- Which codecs SLNG offers; the IP addresses its SIP traffic comes from.
- Whether the number must be linked to the trunk for outbound caller ID.
- Whether the Vonage account is out of trial, and whether Fraud Defender allows Spain for Voice.
- The per-minute price to Spanish mobiles, and whether the US caller ID arrives intact.
- The campaign's dispatch and polling against the live API (`call_id`, `call_ended_at`).
- Call transfer to a person (SLNG `transfer_call`, on the pitch's roadmap): according to [Synthflow's guide](https://docs.synthflow.ai/sip-with-vonage), Vonage does not support SIP REFER, so cold transfers fail on a Vonage trunk. Not tested.
- Two Vonage support articles above were read only through a search summary: the support site refuses automated reads.

## Sources

- SLNG: [telephony overview](https://docs.slng.ai/guides/agents/telephony/overview.md) · [outbound](https://docs.slng.ai/guides/agents/telephony/outbound.md) · [inbound](https://docs.slng.ai/guides/agents/telephony/inbound.md) · [dispatch calls](https://docs.slng.ai/guides/agents/telephony/dispatch-calls.md) · [debug a call](https://docs.slng.ai/guides/agents/debug-a-call.md) · [features](https://docs.slng.ai/concepts/agents/features.md) · [dispatch call API](https://docs.slng.ai/api-reference/calls/dispatch-call.md) · [get call API](https://docs.slng.ai/api-reference/calls/get-call.md) · [SIP trunk options API](https://docs.slng.ai/api-reference/agents/list-sip-trunk-options.md)
- Vonage: [SIP Dashboard](https://developer.vonage.com/en/sip/sip-dashboard) · [SIP technical details](https://developer.vonage.com/en/sip/technical-details) · [phone numbers and caller ID](https://developer.vonage.com/en/voice/voice-api/concepts/numbers) · [Asterisk with a trunk](https://developer.vonage.com/en/sip/configure/asterisk-new) · [legacy Asterisk](https://developer.vonage.com/en/sip/configure/asterisk-legacy) · [Programmable SIP](https://developer.vonage.com/en/voice/voice-api/concepts/programmable-sip) · [NCCO reference](https://developer.vonage.com/en/voice/voice-api/ncco-reference) · [Pricing API](https://developer.vonage.com/en/api/pricing) · [authentication](https://developer.vonage.com/en/getting-started/concepts/authentication) · [numbers in the dashboard](https://developer.vonage.com/en/numbers/guides/number-management) · [trial limits](https://api.support.vonage.com/hc/en-us/articles/212554438-What-are-the-limitations-of-a-trial-account) · [Fraud Defender countries](https://api.support.vonage.com/hc/en-us/articles/10283720577052-How-to-allow-my-SMS-or-Voice-Traffic-to-only-some-countries-using-Fraud-Defender)
- Third-party Vonage guides: [Synthflow](https://docs.synthflow.ai/sip-with-vonage) · [Retell](https://docs.retellai.com/deploy/vonage)
- Spain: [Orden TDF/149/2025](https://www.boe.es/buscar/act.php?id=BOE-A-2025-2870), art. 5.1
