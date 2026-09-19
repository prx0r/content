# Protocols

## Content gates (three)

Every signal must pass all three before rendering.

### evidence-fresh-v1

Proof must have evidence_refs and observed_at. No content without a source chain.

### no-duplicate-v1

Same signal_id + template cannot produce two ok receipts. Re-renders return existing content.json.

### claim-resolved-v1

Every on-screen beat traces to a metric, supporting claim, seed verbatim, or source_ids.

## Receipt chain

Hash-chained append-only JSONL at `store/content.jsonl`. FAIL is first-class. Tampering breaks the chain. `inspect receipts` verifies.

## Content-worthiness

Large change, large geographic disparity, unexpected divergence, clear ranking, clear winner/loser, clear money implication, clear action.

## Interestingness

magnitude_of_change x confidence x novelty x human_relevance x actionability.

## The content manifest

```json
{
  "template": "anomaly",
  "hook": "...",
  "claim": "...",
  "proof": ["metric fact 1", "metric fact 2"],
  "close": "...",
  "source_ids": ["sig_xxx", "sig_yyy"]
}
```

No prose evidence. No invented metrics. The model phrases, the system discovers.
