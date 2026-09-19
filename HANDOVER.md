# HANDOVER — content-sensor

> 2026-09-19. What exists, what works, what to do next.

## What exists and works

**MCP server** (`mcp_server.py`): 27 tools, stdlib only, stdio. All tested 27/27 returning real content. Registered in opencode config and as pi extension.

**Six signal gardens**, all deterministic, evidence-linked:

| Garden | Data | Emitters |
|--------|------|----------|
| powpowpow | live cards + coins + categories | anomaly, ranking, concept, thesis |
| ukgraph | planning 100 + contracts 100 | geo_signal, ranking |
| ukproducts | charity margins + eBay solds 100 | flip margin |
| ashe | ASHE 13,596 rows | wage change YoY |
| hpi | Land Registry 379 rows | type divergence |
| painful tasks | 5 workflows | delay penalties |

**Pipeline**: Signal -> interestingness score -> proof -> gates -> hook/claim/proof/close -> Edge TTS narration -> ffmpeg brand mix -> HyperFrames 9:16 render -> lineage JSONL.

**Dashboard** (`https://watch.moltwork.com`): left sidebar video queue, center full-size player, approve writes receipt. Chat: `create`, `signals`, `videos`, `queue`, `generate`, `approve`.

**Pi agent**: 6 tools via MCP stdio, OpenCode Go thinking, tested.

**Jev**: OpenRouter `typesafe/jev-1.13`, live rubric scoring, deterministic fallback.

**Brand kit**: $0 ffmpeg stings mixed into every render.

**25 videos** in queue, all 25+ seconds with narration and mix.

## What's missing

Jev needs env key for live routing. Taisly needs API keys for publish. Stable Audio brand kit needs Kaggle GPU run. Breadup has no sold data. ASHE is snapshot not time-series. No retention measurement. No YouTube OAuth. No content quality scoring before render. One template only. Supertonic installed but not wired.

## What to do next

Wire Jev quality scoring, add 5-6 motion recipes from video-talkcraft, pull daily data for time-series, wire YouTube OAuth, pull real analytics back, feed retention into Jev for route selection, build experiment protocol. Later: Stable Audio, Supertonic, Breadup, multi-variant A/B.

## Key files

`mcp_server.py` (everything), `core/gates.py` (three gates), `core/receipt.py` (hash chain), `docs/deterministic-view-spec.md` (architecture), `pi-extension/content-sensor.ts` (pi bridge), `registry/processors.yaml` (capabilities).

## Known gotchas

Lineage stores all renders including stale 8s ones (deduped at query). Renders die at 90% disk without low-memory mode. KAS cards have rigged values excluded with notes. Dash auth hardcoded in JS. OpenCode Zen Jev blocked from this VPS.
