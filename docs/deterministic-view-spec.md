# Deterministic view over graph signals (V1 spec)

> Content is just another consumer of the same endpoint. Don't build a
> separate "content intelligence" system yet.

## Core abstraction

```text
RAW DATA
   ↓
TRANSFORM
   ↓
FACTS / MEASUREMENTS
   ↓
GRAPH
   ↓
QUERY
   ↓
MUSE ENDPOINT
   ↓
CONTENT
```

## Canonical garden endpoints

UKGraph:

```text
GET /signals/top
GET /signals/changes
GET /signals/anomalies
GET /rankings/:metric
GET /compare/:a/:b
GET /places/:place/summary
```

PowPowPow:

```text
GET /signals/top
GET /signals/changes
GET /signals/anomalies
GET /resources/:resource
GET /compare/:a/:b
GET /economics/:resource
```

Each endpoint returns the same normalized signal object:

```json
{
  "id": "sig_123",
  "type": "anomaly",
  "title": "Electrician vacancy pressure rose sharply in Bristol",
  "claim": "Vacancy pressure is up 31% while advertised wages rose 12%.",
  "why": "Demand increased faster than available labour supply.",
  "entities": ["electricians", "Bristol"],
  "metrics": [
    { "name": "vacancy_pressure", "value": 31, "unit": "%" },
    { "name": "advertised_wage_change", "value": 12, "unit": "%" }
  ],
  "evidence": [],
  "timespan": "30d",
  "confidence": 0.91,
  "updated_at": "2026-09-19T..."
}
```

## Signal detectors (deterministic, auditable)

No LLM searching the graph for stories. Deterministic transforms emit
candidate signals when conditions hold:

```text
Δ > threshold
z-score > threshold
rank changes materially
two correlated metrics diverge
new local maximum/minimum
cross-sectional outlier
constraint score changes
```

Example:

```python
if vacancy_pressure_30d > 20 and wage_change_30d > 5:
    emit_signal("labour_shortage")
```

The model only phrases — it never discovers the fact.

## Interestingness scorer

```text
interestingness =
  magnitude_of_change
× confidence
× novelty
× human_relevance
× actionability
```

No audience ontology yet.

## Content queries (six)

```text
CHANGE       "What changed?"
WHY          "Why is this changing?"
WHERE        "Where is this strongest?"
COMPARE      "What beats what?"
OPPORTUNITY  "What can someone do because of this?"
WARNING      "Who is exposed to this?"
```

One seed signal spawns queries; the worker re-queries the graph for the
supporting neighbourhood (2–4 strongest facts) and renders without
hallucinating anything.

## Render manifest

```json
{
  "template": "opportunity",
  "hook": "Graphic designers may want to look at these three jobs.",
  "claim": "UK graphic-design vacancies are down 27% over 12 months.",
  "proof": [
    "Creative ops vacancies +14%",
    "Motion roles +9%",
    "Marketing automation +21%"
  ],
  "close": "These require the least skill-distance from graphic design.",
  "source_ids": ["sig_4821", "sig_991", "sig_233"]
}
```

Renderer maps fields to scenes. Nothing else thinks.

## Content-worthiness gate

A signal is eligible for content if one of these is true:

```text
large change
large geographic disparity
unexpected divergence
clear ranking
clear winner/loser
clear money implication
clear action somebody can take
```

## Shared expansion (Muse and content use the same logic)

```text
current occupation
→ stress signal
→ adjacent occupations
→ skill distance
→ demand
→ earnings
→ geography
```

Muse asks for retraining advice; content asks for opportunity content.
Same graph query underneath.

## V1 endpoints to implement

1. `GET /signals`
2. `POST /expand-signal/:id`
3. `POST /content/from-signal/:id`

## V1 completion criteria

1. PowPowPow and UKGraph each expose `/signals`.
2. `/signals` returns transformed, evidence-linked findings.
3. Muse can answer a query using those signals.
4. A worker takes one signal → `content.json`.
5. HyperFrames renders `content.json` → one clean vertical MP4.
6. `signal_id → video_id` stored; every video attached to its graph fact.
7. Publish manually initially.

Source-of-truth relation:

$$
\boxed{\text{graph signal} \rightarrow \{\text{Muse},\text{API},\text{content}\}}
```
