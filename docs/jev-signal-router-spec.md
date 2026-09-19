# Jev selection layer over graph signals (spec)

> Jev chooses; code executes. Don't let Jev create arbitrary output.

## Status (2026-09-19)

Jev **is released** (TypeSafe announced September 14–15, 2026, current
model `jev-1.13.0`), but direct TypeSafe API is early-access/waitlist
gated. Build through OpenRouter today (`typesafe/jev-1.13`, listed at
$0.042/M input tokens, $0 output), keep the interface provider-neutral,
switch to TypeSafe direct later.

## Reference repos (`/home/ubuntu/content`, gitignored)

| Dir | Upstream | Role |
|-----|----------|------|
| `jev-ultrafast` | `browser-use/jev-ultrafast` (MIT) | Best architecture: state + constrained choices → probabilities → code executes |
| `typesafe-jev-examples` | `rajivkuriakose/typesafe-jev-examples` | Easiest start: OpenRouter-ready examples |
| `typesafe-ai-playground` | `markjaquith/typesafe-ai-playground` | Provider abstraction (TypeSafe direct + OpenRouter Decisions) |
| `awesome-jev-by-typesafe` | `Anil-matcha/awesome-jev-by-typesafe` | Pattern library: Choice, Score, Noul |
| `awesome-jev` | `hellogumbo/awesome-jev` | Directory for stealing patterns |

## Placement in the pipeline

```text
DETERMINISTIC GRAPH
detect raw candidate signals
        ↓
JEV
rank / classify / gate / choose framing
        ↓
LLM
write 20-second script
        ↓
video renderer
```

Jev is the **selection layer** between graph and generative model — not
for writing content. Candidate framing choices stay bounded
(`ANOMALY`, `RANKING`, `OPPORTUNITY`, `COMPARE`, `IGNORE`) with
probabilities retained, so the pipeline stays inspectable and
backtestable.

## Router questions per signal

```text
- is this materially interesting?      (score 0-10)
- which audience is most affected?     (choice)
- which framing fits best?             (choice)
- is there an actionable monetary implication?  (noul)
- which content template?              (choice)
```

Example state + questions:

```json
{
  "state": {
    "signal": {
      "occupation": "graphic designers",
      "vacancy_change_12m": -27,
      "wage_change_12m": -4,
      "ai_exposure": 0.88,
      "adjacent_roles": 7
    }
  },
  "questions": {
    "interest": { "type": "score", "min": 0, "max": 10 },
    "frame": {
      "type": "choice",
      "criteria": {
        "job_stress": "...",
        "retraining": "...",
        "opportunity": "...",
        "geographic": "...",
        "ignore": "..."
      }
    }
  }
}
```

## Cost posture

At listed pricing, millions of small judgments are infrastructure-cost,
not something to optimize prematurely. Rank freely; gate rendering.

## OpenRouter vs direct

- Now: OpenRouter Decisions endpoint, model `typesafe/jev-1.13`.
- Later: `POST https://api.typesafe.ai/v1/systemone` with `jev-latest`
  when access lands.
- Content MCP keeps one `route_signal` interface; provider switches by
  env, and every verdict records its origin (`jev` vs `deterministic`
  fallback) so nothing is ever misrepresented.
