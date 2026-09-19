# Vision

## One sentence

Content is a deterministic view over graph signals.

## What this is

A content factory that sits on top of data gardens. The gardens own their facts. The factory owns compilation: turning measured reality into short-form video with receipts.

## What this is not

Not a creative director. Not an audience optimizer. Not a platform play. Not a "content intelligence" system. A compiler.

## The core principle

**Every number on screen traces to a source row.**

No prose evidence, ever. No invented metrics. No hallucinated claims. The model phrases, it never discovers the fact. If a signal doesn't have metrics and evidence, it doesn't get a proof, doesn't get a content manifest, doesn't get rendered. The gate is the gate.

## The content loop

```text
graph fact
  -> interestingness score
  -> content query (WHY / CHANGE / COMPARE / OPPORTUNITY / WARNING)
  -> graph expansion (supporting neighbourhood)
  -> render manifest (hook / claim / proof / close)
  -> narration + brand mix
  -> HyperFrames render
  -> lineage receipt
  -> review queue
  -> approve (human gate)
  -> publish
  -> measure
  -> learn
```

## The visual cost ladder

Cheap first, expensive only when attention justifies it:

```text
chart / map / text       $0.00
existing asset + motion  $0.00
stock footage            $0.00
AI still + motion        ~$0.001-0.02
avatar                   ~$0.05-0.50
full generative video    ~$0.10-1+
```

The director picks the cheapest sufficient representation. Creative spend flows toward scarce attention response.

## The five principles

### 1. Evidence-linked

No content exists without a proof chain. Every signal has source files and timestamps. Every gate checks evidence freshness.

### 2. Deterministic first

Signal detection is deterministic transforms over graph data. No LLM searching for stories. Thresholds, z-scores, rank changes, divergences. The model phrases, the system discovers.

### 3. Worthiness-gated

Not every graph update becomes content. Interestingness scoring filters routine updates. Content-worthiness rules prevent noise: large change, large geographic disparity, unexpected divergence, clear ranking, clear money implication, clear action.

### 4. Receipt-chained

Every edge produces a receipt. Hash-chained, append-only, FAIL first-class. You can trace any video back to its source row through the chain. The chain is verifiable.

### 5. Human gate before publish

No content publishes without approval. The approve button writes a manual-pending receipt. Machine execution, human authorization.

## The architecture principle

Own the intent + graph + contracts + receipts. Everyone else owns implementation. HyperFrames is a dependency. Edge TTS is a dependency. Jev is a dependency. None are owned. All are replaceable.

```text
OUR ENDPOINT owns:
  intent
  dependency graph
  contracts (gates, receipts)
  proofs
  lineage

EVERYONE ELSE owns:
  TTS implementation
  video renderer
  avatar engine
  subtitle engine
  video model
  platform uploader
  motion engine
  image generator
```

Tomorrow HyperFrames dies. Install `some-new-renderer` that provides `render.vertical`. Nothing upstream changes. Exactly like influence.

## Current focus (September 2026)

### Phase 1: quality

Wire Jev for content quality scoring. Add 5-6 motion recipes from video-talkcraft. Pull daily data for time-series signals. Make the dashboard content tab show render stats.

### Phase 2: feedback loop

Wire YouTube OAuth. Pull real analytics. Feed retention into Jev for route selection. Build experiment protocol: hypothesis -> hook variants -> publish -> measure -> update priors.

### Phase 3: premium

Stable Audio brand kit on Kaggle GPU. Supertonic local TTS. Breadup sold data. Multi-variant A/B testing.

## The relationship to the gardens

PowPowPow owns its facts. UKGraph owns its facts. The content factory reads them, ranks them, renders them, receipts them. Muse reads the same signals. The API reads the same signals. One source, three consumers:

```text
graph signal -> {Muse, API, content}
```
