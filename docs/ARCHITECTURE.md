# Architecture

## The pipeline

```text
RAW DATA (datagarden canonical observations)
  ↓
TRANSFORMS (deterministic signal emitters)
  ↓
GRAPH (signals with metrics, evidence, confidence)
  ↓
SCORING (interestingness: magnitude x confidence x relevance x actionability)
  ↓
WORTHINESS GATE (large change / divergence / ranking / money / action)
  ↓
ROUTING (Jev verdict: frame, monetary, template)
  ↓
CONTENT COMPILATION (hook / claim / proof / close / source_ids)
  ↓
GATES (evidence-fresh / no-duplicate / claim-resolved)
  ↓
NARRATION (Edge TTS, provider-neutral)
  ↓
AUDIO MIX (brand sting + whoosh + bed ducked under voice)
  ↓
RENDER (HyperFrames 9:16, dependency graph resolves processor)
  ↓
LINEAGE (signal_id -> content_id -> video_id, receipt-chained)
  ↓
REVIEW (dash: watch, approve -> manual-pending receipt)
  ↓
PUBLISH (Taisly or manual)
  ↓
MEASURE (performance metrics back into receipt chain)
```

## The MCP

27 tools over stdio. Same shape as datagarden MCP servers. Registered in opencode config and as pi extension.

### Tool categories

**Signal layer** — what happened:
`signals_top` / `rank_signals` / `route_signal` / `expand_signal`

**Content layer** — what to say:
`content_from_signal` / `build_content` / `list_templates` / `concepts_top` / `concept_explain` / `relationships` / `theses_top`

**Execution layer** — make it:
`run` / `ingest` / `compile` / `render_video` / `render_narration` / `publish` / `measure`

**System layer** — check it:
`content_status` / `lineage` / `inspect`

## The dependency graph (influence kernel)

```text
Proof
  -> Processor (propose-only, forbidden keys)
  -> Artifact (traversable chain)
  -> Receipt (hash-chained, append-only, FAIL first-class)
  -> Gates (evidence-fresh / no-duplicate / claim-resolved)
```

The MCP never knows how to make a video. It knows:
- INPUT: ContentSignal
- DESIRED OUTPUT: ContentArtifact
- AVAILABLE PROCESSORS: anything installed / configured
- DEPENDENCY GRAPH: what needs to happen between input and output

## The processor registry

`registry/processors.yaml` declares what each cloned repo provides:

| Processor | Provides | Cost | Status |
|-----------|----------|------|--------|
| hyperframes | render.vertical, animation.svg, captions.render | local | live |
| clipforge_zero | render.vertical, voice.tts, captions.render | $0 | live |
| jev | judge.choice, judge.score, judge.rank | metered | live-fallback |
| supertonic | voice.tts | local | stub |
| voicestudio | voice.tts, voice.clone | local | stub |
| stable_audio | audio.sfx, audio.bed, audio.sting | kaggle-gpu | stub |
| socheli | script, storyboard, render.vertical, publish.* | metered | registry-only |
| openshorts | clip.long_to_short, captions, dubbing, publish.* | metered | registry-only |
| taisly | publish.* | free-client | registry-only |

## The module registry

`registry/modules.yaml` defines reusable compositions:

- `clean_signal_short` — the current default: rank -> script -> voice -> render
- `narrated_chart_short` — adds chart scene
- `avatar_explainer` — presenter-led (needs avatar provider)
- `ugc_commerce` — product commerce short (needs clipforge)

## The template registry

`registry/templates.yaml` maps signal types to scene compositions:

- `anomaly` -> hook, hero_metric, evidence, implication, source
- `ranking` -> hook, winner, list, source
- `comparison` -> hook, side_a, side_b, verdict, source
- `what_changed` -> hook, before, after, source
- `map` -> hook, map_focus, metric, source
- `why` -> hook, claim, mechanism, source
- `opportunity` -> hook, claim, proof, close, source

## Data flow through the system

```
datagarden/canonical/*.jsonl
  ↓ signals_top (transform)
signal JSON {id, type, metrics, evidence, confidence}
  ↓ content_from_signal (compile)
content JSON {hook, claim, proof, close, source_ids, template}
  ↓ render_narration (TTS)
content.narration.mp3
  ↓ _mix_audio (brand kit)
content.mix.mp3
  ↓ render_video (HyperFrames)
project/renders/*.mp4
  ↓ lineage log
store/lineage.jsonl {signal_id, content_id, video_id, mp4, rendered_at}
  ↓ inspect
verifiable chain back to source
```
