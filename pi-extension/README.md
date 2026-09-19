# pi extension wiring (this box)

> Policy: OpenRouter key is for Jev decisions only. pi thinks via
> OpenCode Go. The dashboard and pi were already set up — this just
> plugs content in.

- Extension autoloads from `~/.pi/agent/extensions/content-sensor.ts`
  (copy of `content-sensor.ts` here). Spawns the content MCP over
  stdio, registers signals/rank/expand/compile/queue/status tools.
- pi provider `opencode-go` in `~/.pi/agent/models.json`:
  `baseUrl https://opencode.ai/zen/go/v1`, api `openai-completions`,
  model `mimo-v2.5`, key from opencode auth (0600, never in tree).
- Run: `pi -p --provider opencode-go --model mimo-v2.5 --name X "…"`
- Verified: pi called content_signals + content_rank on ukgraph and
  reported the ranked table (session `content-go-1`).
