# content — datagarden content sensor

One-command content factories on top of commodity renderers.
Own the measurements, not the video renderer.

## Architecture

```text
DATAGARDEN verified hypothesis
  -> CONTENT COMPILER (format DB + channel DB + experiment DB)
  -> creative spec
  -> ROUTER (cheapest sufficient visual)
  -> commodity renderer -> MP4
  -> publisher -> YT/IG/FB
  -> analytics -> RESPONSE GARDEN -> updated priors
```

Visual cost ladder: chart/map/text ($0) -> existing asset + motion ($0)
-> stock ($0) -> AI still + motion (~$0.001-0.02) -> avatar (~$0.05-0.50)
-> full generative video (~$0.10-1+). Creative spend flows toward
scarce attention response. Premium only after $0 is locked down.

## Repos (all --depth 1, 2026-09-19)

| Dir | Upstream | Role |
|-----|----------|------|
| socheli | Socheli/socheli | Control-plane reference: research->plan->create->publish->analyze, Brand Genome, MCP |
| openshorts | Serialabs/openshorts | Ready-made all-in-one, ~$0.65 UGC path |
| moneyprinterturbo | harry0703/MoneyPrinterTurbo | Boring reliable $0 base: stock + TTS + captions + direct publish |
| opennolan | het8802/OpenNolan | Agentic editor: FFmpeg / Remotion / HyperFrames patterns to steal |
| open-ai-ugc | Anil-matcha/Open-AI-UGC | Generative actor front end (Veo/Seedance/Grok, pay-per-use) |
| atlas-marketing-studio | AtlasCloudAI/atlas-marketing-studio | Reference-structure + new-info -> new short |
| clipforge-zero | DarkPancakes/clipforge | $0 baseline: Groq-free LLM + Edge TTS + FLUX/fallback + Ken Burns |
| clipforge-commerce | xixihhhh/clipforge | $0 commerce path: Openverse/Wikimedia + Edge TTS + FFmpeg, no key |
| taisly-agent | taisly/agent | Publishing primitive: TikTok/Reels/Shorts/X/FB via SDK/CLI/MCP |

Kalinga skipped: no canonical repo found (Higgsfield-adjacent, ambiguous).

## $0 baseline (verified)

venv at `.venv` (edge-tts, click, requests, fal-client, clipforge-zero installed).
ffmpeg 6.1.1 system. No API keys used.

```bash
.venv/bin/clipforge generate \
  --script "Something strange just happened to GPU economics..." \
  --output test_zero_baseline.mp4
```

Result: 1080x1920 h264 + aac, 16.3s, 414KB, 5 gradient-fallback clips
+ Edge TTS + word-level subs. Proof: `experiments_001_zero_baseline.mp4`.
$0 because --script skips LLM and no FAL key means gradient fallback.

Next $0 steps: Groq free key for topic->script, Openverse/Wikimedia stock
fill via clipforge-commerce, MoneyPrinterTurbo stock+EdgeTTS path,
Taisly publish dry-run. Then A/B hook/caption/BGM variants, then
paid visuals only where attention delta justifies cost.

## MCP: content-sensor (V1, verified end to end)

`mcp_server.py` — stdlib only, same stdio shape as datagarden servers.
Nine tools implementing `docs/deterministic-view-spec.md`:
`signals_top` (powpowpow | ukgraph, scored by interestingness,
worthiness-gated) → `expand_signal` (seed → supporting neighbourhood)
→ `content_from_signal` (CHANGE|WHY|WHERE|COMPARE|OPPORTUNITY|WARNING
→ hook/claim/proof/close/source_ids manifest) → `render_video`
(HyperFrames 9:16 MP4, lineage logged) + `render_narration` ($0 Edge
TTS) + `build_content`, `list_templates`, `content_status`, `lineage`.

Sanity gates are load-bearing: expansion caught KAS rig figures at
$3.3B/day in the source cards — absurd rigs are excluded with notes,
not rendered.

## Jev selection layer (`docs/jev-signal-router-spec.md`)

`route_signal` / `rank_signals`: provider-neutral Jev verdicts
(interest / frame / monetary / template) over deterministic candidates.
OpenRouter Decisions endpoint now (`typesafe/jev-1.13`), TypeSafe direct
later — one interface, origin always reported. No key configured, so the
MCP runs deterministic fallback honestly marked; 401 path tested to fall
back cleanly. Reference repos cloned: `jev-ultrafast`,
`typesafe-jev-examples`, `typesafe-ai-playground`, both awesome lists.

```bash
python3 mcp_server.py --serve   # MCP stdio for agents
```

Verified 2026-09-19: PRL unprofitability signal → content → narration
(177KB) → 9:16 MP4 → `signal_id → video_id` in store/lineage.jsonl.
Publishing still manual. Brand SFX kit pending (Stable Audio recipes).

## Experiment protocol (the proprietary bit)

hypothesis -> experiment def (hook variants x format) -> generate ->
publish -> observe (retention, CTR, comments, follows) -> update
content priors + format genotypes. Everything pixel-related stays
replaceable.
