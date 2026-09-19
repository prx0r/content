# Stack

## What's wired and working

| Component | Status | How |
|-----------|--------|-----|
| HyperFrames render | live | `npx hyperframes render` via mcp_server.py |
| Edge TTS narration | live | `.venv/bin/edge-tts` via render_narration |
| Brand mix (sting/whoosh/bed) | live | ffmpeg sidechain compression via _mix_audio |
| Jev signal ranking | live (fallback) | OpenRouter typesafe/jev-1.13 |
| Pi agent tools | live | content-sensor.ts extension, OpenCode Go thinking |
| Dash review | live | watch.moltwork.com, Content view + chat verbs |
| 6 signal gardens | live | Deterministic emitters in mcp_server.py |
| 3 content gates | live | core/gates.py |
| Hash-chained receipts | live | core/receipt.py, store/content.jsonl |

## What's declared but not wired

| Component | Status | What it needs |
|-----------|--------|---------------|
| Taisly publish | registry | API keys |
| Stable Audio brand | recipes | Kaggle GPU run |
| Supertonic TTS | installed | Wire into render_narration |
| Breadup sold data | 0 rows | Apify or local run |
| YouTube OAuth | manual | Credentials |
| Content quality scoring | not built | judge_content tool |
| Multi-template rendering | 1 template | Port video-talkcraft recipes |
| A/B hook testing | not built | Hook variant generator |
| Retention measurement | not built | YouTube Analytics API |

## Key directories

| Path | Purpose |
|------|---------|
| `mcp_server.py` | All 27 tools, stdlib only |
| `core/` | influence kernel (proof, processor, artifact, receipt, gates) |
| `registry/` | processors, modules, templates, theses (YAML) |
| `channels/` | ukgraph, powpowpow profiles |
| `templates/` | anomaly, ranking, comparison, map, causal, opportunity |
| `brand/` | sting.wav, whoosh.wav, bed.wav, build.sh |
| `pi-extension/` | content-sensor.ts (pi tool bridge) |
| `store/` | proofs, lineage, content.json, audio, renders |
| `tests/` | 8 kernel tests |
| `docs/` | all specs and this documentation |

## Tokens

| Service | Location | Purpose |
|---------|----------|---------|
| OpenRouter | vault OPENROUTER_API_KEY | Jev decisions |
| OpenCode Go | ~/.local/share/opencode/auth.json | pi + MCP thinking |
| Dash | hardcoded in static/index.html | zero-paste browser access |
| HF | vault HF_TOKEN | Kaggle GPU (pending) |
| Kaggle | vault KAGGLE_API_TOKEN | GPU renders (pending) |

## Rendering pipeline

```text
content.json
  ↓ render_narration (edge-tts)
content.narration.mp3
  ↓ _mix_audio (brand kit + sidechain)
content.mix.mp3
  ↓ render_video (hyperframes --low-memory-mode)
project/renders/*.mp4 (1080x1920, h264+aac)
```

Duration: narration length + 1.2s padding. Brand mix loops bed, ducks under voice, stings head, whooshes transition.
