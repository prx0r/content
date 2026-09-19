# content

Content factory for prx0r's data garden system. Deterministic pipeline from graph signals to rendered 9:16 MP4s with narration, sound design, and receipt-chained lineage.

**Live stack:** HyperFrames (render) + Edge TTS (narration) + ffmpeg brand kit (sting/whoosh/bed) + OpenRouter Jev (ranking) + OpenCode Go (pi thinking) + influence dash (review/approve). No API keys required for the $0 path.

## Quick start

```bash
# signals
python3 mcp_server.py signals_top '{"garden":"ukgraph","limit":3}'

# rank + route (Jev or deterministic fallback)
python3 mcp_server.py rank_signals '{"garden":"ukgraph","limit":3}'

# generate end-to-end (proof → gate → narrate → mix → render → lineage)
python3 mcp_server.py run '{"signal_id":"sig_52567c66646e","query":"OPPORTUNITY"}'

# review queue
python3 mcp_server.py lineage '{"limit":10}'

# dash
python3 mcp_server.py inspect '{"target":"receipts"}'
```

## Architecture

```text
SIGNALS (deterministic transforms over graph data)
   ↓ interestingness scoring + worthiness gate
CONTENT COMPILER (hook / claim / proof / close / source_ids)
   ↓ content gates (evidence-fresh, no-duplicate, claim-resolved)
JUDGE (Jev or fallback: interest / frame / monetary / template)
   ↓
RENDERER (HyperFrames 9:16, audio mixed in)
   ↓
LINEAGE (signal_id → video_id, hash-chained receipts)
   ↓
DASHBOARD (review / approve / measure → publish receipt)
```

## MCP tools (27)

### Signal layer
`signals_top` · `rank_signals` · `route_signal` · `expand_signal`

### Content layer
`content_from_signal` · `build_content` · `list_templates` · `concepts_top` · `concept_explain` · `relationships` · `theses_top`

### Execution layer
`run` · `ingest` · `compile` · `render_video` · `render_narration` · `publish` · `measure`

### System layer
`content_status` · `lineage` · `inspect`

## Gardens

| Garden | Data source | Signal type |
|--------|------------|-------------|
| powpowpow | v1_live_cards.json + coins.py | anomaly, ranking, concept, thesis |
| ukgraph | planning + contracts JSONL | geo_signal, ranking, comparison |
| ukproducts | charity margins + eBay solds | ranking (flip margins) |
| ashe | ASHE earnings JSONL | ranking (wage change YoY) |
| hpi | Land Registry HPI CSV | comparison (type divergence) |
| boring | painful_tasks.py | ranking (delay penalties) |

## Content review

25 videos in queue (as of 2026-09-19). All 25+ seconds with narration mixed in. Dash at `https://watch.moltwork.com` with full video playback in editor area.

## Pi agent

Extension at `pi-extension/content-sensor.ts` (also installed at `~/.pi/agent/extensions/`). Six tools: `content_signals`, `content_rank`, `content_expand`, `content_compile`, `content_queue`, `content_status`. Pi thinks via OpenCode Go, tools via content MCP stdio.

## Directory layout

```
content/
├── mcp_server.py          # all 27 tools, stdlib only
├── core/                  # influence kernel (proof, processor, artifact, receipt, gates)
├── registry/              # processors, modules, templates, theses (YAML)
├── channels/              # ukgraph, powpowpow profiles (YAML)
├── templates/             # anomaly, ranking, comparison, map, causal, opportunity
├── brand/                 # sting.wav, whoosh.wav, bed.wav + build.sh
├── pi-extension/          # content-sensor.ts (pi tool bridge)
├── docs/                  # specs (deterministic-view, influence-kernel, jev, powpowpow-knowledge-compiler, pi-agent-path)
├── tests/                 # 8 kernel tests (proof refusal, forbidden keys, duplicate gate, chain verify)
├── receipts/              # content.jsonl (hash-chained, append-only)
├── store/                 # proofs, lineage, content.json, narration.mp3, mix.mp3, projects/*/renders/*.mp4
├── hyperframes/           # renderer (gitignored, cloned --depth 1)
├── clipforge-zero/        # $0 fallback renderer (gitignored)
├── video-talkcraft/       # motion grammar reference (gitignored)
├── socheli/               # control-plane reference (gitignored)
├── openshorts/            # all-in-one reference (gitignored)
├── moneyprinterturbo/     # stock+TTS base (gitignored)
├── opennolan/             # agentic editor patterns (gitignored)
├── open-ai-ugc/           # generative actor front end (gitignored)
├── atlas-marketing-studio/ # reference-structure patterns (gitignored)
├── taisly-agent/          # publishing primitive (gitignored)
├── jev-ultrafast/         # Jev architecture reference (gitignored)
├── typesafe-jev-examples/ # Jev wire format reference (gitignored)
├── typesafe-ai-playground/ # Jev provider abstraction (gitignored)
├── awesome-jev/           # Jev pattern directory (gitignored)
├── awesome-jev-by-typesafe/ # Jev use cases (gitignored)
├── supertonic-tts/        # local TTS reference (gitignored)
├── voicestudio/           # multi-engine TTS reference (gitignored)
├── pocket-tts/            # voice cloning reference (gitignored)
└── ccvideo/               # restrained visual aesthetic reference (gitignored)
```

## Tokens / keys

| Service | Where | Purpose |
|---------|-------|---------|
| OpenRouter | `main` vault (OPENROUTER_API_KEY) | Jev decisions only |
| OpenCode Go | `~/.local/share/opencode/auth.json` | pi thinking + content MCP |
| HF | `main` vault (HF_TOKEN) | Kaggle Stable Audio (pending) |
| Kaggle | `main` vault (KAGGLE_API_TOKEN) | GPU renders (pending) |

Dash token hardcoded in `static/index.html` for zero-paste access.
