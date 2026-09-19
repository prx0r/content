# Content as dependency graph (influence-kernel spec)

> Copy influence's dependency-graph architecture, not a monolithic
> "content generator". Our endpoint owns intent + graph + contracts +
> receipts; everyone else owns implementation.

## Canonical model

The MCP never knows "how to make a video". It knows:

```text
INPUT
ContentSignal

DESIRED OUTPUT
ContentArtifact

AVAILABLE PROCESSORS
anything currently installed / configured

DEPENDENCY GRAPH
what needs to happen between input and output
```

```text
UKGraph signal
     │
     ▼
content.compile
     │
     ▼
ContentSpec
     │
     ├── requires narration
     ├── requires chart
     ├── requires captions
     ├── requires render
     └── requires publish
             │
             ▼
      DEPENDENCY RESOLVER
             │
    ┌────────┼─────────┬──────────┐
    ▼        ▼         ▼          ▼
   Jev    TTS engine  HyperFrames  publisher
```

## Primitives (copied from influence)

```text
Proof
Processor
Module
Artifact
Receipt
```

### Proof

Immutable source evidence. No video exists without a proof chain.

```json
{
  "proof_id": "proof_123",
  "kind": "graph_signal",
  "source": "ukgraph",
  "subject": "graphic_design",
  "claims": [],
  "evidence_refs": [],
  "observed_at": "..."
}
```

### Processor

Typed inputs/outputs. Adapters over the cloned repos, not their
architecture absorbed into ours:

```text
jev.rank            signal → ranked_signal
script.short        ranked_signal → script
voice.supertonic    script → audio
voice.qwen          script → audio
chart.svg           proof → svg
render.hyperframes  content_spec + assets → mp4
render.socheli      content_spec → mp4
publish.youtube     mp4 + metadata → published_post
```

### Module

Reusable composition of processors (e.g. `clean_signal_short`,
`avatar_explainer`). The module doesn't care whether `voice` resolves
to Supertonic, Qwen, Cartesia or next Thursday's model.

## Capability registry (`registry/processors.yaml`)

Each processor declares what it provides, cost, quality,
determinism. Resolution selects the graph; later optimize for
cheapest / fastest / local-only / highest-quality without changing
the pipeline.

## MCP surface (tiny)

```text
content.ingest     anything → ContentSource
content.compile    source + channel + objective → ContentSpec
content.render     spec → artifact via dependency graph
content.publish    platform adapters (manual first)
content.measure    read performance back
content.run        signal → finished post (convenience)
content.inspect    graph, processors, costs, artifacts, receipts, proofs
```

## Dependency DAG

```text
signal:ukgraph:9981
        │
        ▼
   jev.score_signal
        │
        ▼
   compile.short
        │
        ├──────────────┐
        ▼              ▼
 qwen.voice       chart.svg
        │              │
        └──────┬───────┘
               ▼
     hyperframes.render
               │
               ▼
         video.mp4
          │        │
          ▼        ▼
      youtube    instagram
          │        │
          └───┬────┘
              ▼
        performance
```

Every edge produces an artifact/receipt. Traverse video → spec →
claim → signal → transformation → observation → source.

## Separation rule

Own: ContentSource, ContentSignal, ContentSpec, SceneSpec, AudioSpec,
PublishSpec, PerformanceObservation, Processor, Capability, Artifact,
Receipt. Never own: TTS, renderer, avatar, subtitles, video model,
uploader, motion engine, image generator.

Templates are dependencies too (`/template-registry`): steal motion
recipes from video-talkcraft, evidence cards from ccvideo,
skills/presets from HyperFrames, storyboarding/QA from Socheli,
publication from OpenShorts, viral structure from Monid, UGC patterns
from Pamba — as canonical recipe definitions, not source spaghetti.

## Performance receipts (the learnable loop)

Publication receipt + 1h/3h/24h views, hold rate, completion, likes,
comments, shares, saves, clicks. Eventually Jev chooses not only the
signal but the dependency route from historical performance:

```text
signal type X + template Y + voice Z + renderer Q → performance
```

## Repo structure

```text
content/
├── mcp/
│   └── server.py
├── core/
│   ├── source.py
│   ├── spec.py
│   ├── artifact.py
│   ├── receipt.py
│   ├── graph.py
│   └── resolver.py
├── registry/
│   ├── processors.yaml
│   ├── modules.yaml
│   └── templates.yaml
├── processors/
│   ├── jev/
│   ├── hyperframes/
│   ├── socheli/
│   ├── openshorts/
│   ├── voice/
│   └── publish/
├── templates/
│   ├── anomaly/
│   ├── ranking/
│   ├── comparison/
│   ├── map/
│   └── causal/
├── channels/
│   ├── ukgraph.yaml
│   └── powpowpow.yaml
└── receipts/
```

V1 needs only: Jev + one LLM + one TTS + HyperFrames + YouTube
(manual). Build by forking the architectural kernel from influence.
