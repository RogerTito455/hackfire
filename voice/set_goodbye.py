"""Give a deployed SLNG agent's end_call a Spanish goodbye. Run it after every `unmute deploy`.

SLNG's end_call says "Thanks for calling. Goodbye!" unless the attachment carries a goodbye_message,
and unmute 0.5.5 cannot set one (it refuses `inject:` on end_call). A PATCH cannot change tool
attachments, so this downloads the agent's full config, sets the goodbye and PUTs it back; nothing
else changes. Reads SLNG_API_KEY from the environment.

    set -a; . ./.env; set +a
    python3 voice/set_goodbye.py 0f035ccc-10d8-4de8-8142-abf4dc484fd8 "Hasta luego."   # resident
    python3 voice/set_goodbye.py 6d1a743a-4a0e-42b2-aa3f-5052c247137c "Hasta luego."   # coordinator
"""

import json
import os
import sys
import urllib.error
import urllib.request

AGENTS_URL = "https://api.agents.slng.ai/v1/agents"
END_CALL_TOOL_ID = "952eb6b1-fa3f-47a5-9ec5-ccee65d5eba3"
# Fields GET returns that PUT refuses.
READ_ONLY = {
    "id", "created_at", "updated_at", "deleted_at", "organisation_id", "livekit_deployment",
    "models_validation_error", "tools", "template_variables",
}


def call(method: str, url: str, body: dict | None = None) -> tuple[int, dict]:
    request = urllib.request.Request(
        url,
        method=method,
        headers={"Authorization": f"Bearer {os.environ['SLNG_API_KEY']}", "Content-Type": "application/json"},
        data=json.dumps(body).encode() if body is not None else None,
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return response.status, json.loads(response.read() or b"{}")
    except urllib.error.HTTPError as error:
        return error.code, json.loads(error.read() or b"{}")


def main(agent_id: str, goodbye: str) -> int:
    status, agent = call("GET", f"{AGENTS_URL}/{agent_id}")
    if status >= 300:
        print(f"GET {status}: {agent}")
        return 1
    body = {key: value for key, value in agent.items() if key not in READ_ONLY}
    # GET returns the call variables as template_variables; PUT takes defaults plus options.
    variables = agent.get("template_variables") or {}
    if variables:
        body["template_defaults"] = {name: v.get("default", "") for name, v in variables.items()}
        body["template_variable_options"] = {name: {"required": v.get("required", True)} for name, v in variables.items()}
    for ref in body["tool_refs"]:
        if ref["tool_id"] == END_CALL_TOOL_ID:
            ref["config_overrides"] = {
                "type": "end_call",
                "goodbye_message": {"segments": [{"type": "literal", "value": goodbye}]},
            }
    status, answer = call("PUT", f"{AGENTS_URL}/{agent_id}", body)
    print(f"PUT {status}" if status < 300 else f"PUT {status}: {json.dumps(answer)[:500]}")
    return 0 if status < 300 else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1], sys.argv[2]))
