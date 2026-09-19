# Devin (Cognition)

**Used for:** extension 3 (#19): Devin iterates on the fallback spread model until an IoU validator against the real hotspots passes. The challenge requires that code, not a person, judges each attempt, and that a failed first attempt gets fixed autonomously.
**Status:** extension, last in line; most likely only mentioned in the pitch
**Owner:** Rosa

## Access

Ask the Cognition mentors for an organisation and credits. Devin needs:

- **An API key** starting with `cog_` (legacy `apk_` keys do not work with the MCP). A service-user key is recommended.
- **GitHub access**: Settings → Connections → GitHub → Add Connection, all or selected repositories. It must be done by an admin of the GitHub account that owns the repo, so Roger (`RogerTito455/hackfire`).

## Two MCP servers

| Server | Auth | What for |
|---|---|---|
| DeepWiki, `https://mcp.deepwiki.com/mcp` | None | Questions about any public repo. **Already in `.mcp.json`**; useful now, not only for the extension |
| Devin, `https://mcp.devin.ai/mcp` | `cog_` key | Start and follow Devin sessions, playbooks, knowledge. Personal, user scope |

```bash
claude mcp add --scope user --transport http devin https://mcp.devin.ai/mcp \
  -H "Authorization: Bearer <cog_ key>"
```

## Starting a session from code

```bash
curl -X POST "https://api.devin.ai/v3/organizations/$DEVIN_ORG_ID/sessions" \
  -H "Authorization: Bearer $DEVIN_API_KEY" \
  -H 'Content-Type: application/json' \
  -d '{"prompt": "…", "repos": ["RogerTito455/hackfire"], "max_acu_limit": 5}'
```

(Not yet run.) Only `prompt` is required. Commenting `/devin <prompt>` on an open pull request also starts a session.

For #19 the loop would be: a script computes IoU between the predicted cone and the hotspots that actually burned; it starts a Devin session with the failing score; Devin edits the model and reruns the script until it clears the threshold. The validator must exist before Devin is involved.

## Sources

- Devin MCP: https://docs.devin.ai/work-with-devin/devin-mcp
- DeepWiki MCP: https://docs.devin.ai/work-with-devin/deepwiki-mcp
- Authentication: https://docs.devin.ai/api-reference/authentication
- Create session: https://docs.devin.ai/api-reference/v3/sessions/post-organizations-sessions
- GitHub: https://docs.devin.ai/integrations/gh
