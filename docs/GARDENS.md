# Gardens

Six data gardens feed signals into the content factory. Each has its own emitter, its own data source, and its own signal type.

## PowPowPow (resources forest)

**Data:** `v1_live_cards.json` (hardware profitability), `coins.py` (registry), `categories.py` (taxonomy)

**Signals:**
- **Anomaly**: Which coins have no profitable hardware at current prices
- **Ranking**: Least-unprofitable cross-asset comparison
- **Concept**: Per-coin explainers (QUBIC, XMR, PRL, etc.) at multiple angles (explain / why-now / economics / hardware)
- **Thesis**: Curated evergreen questions (useful-PoW, privacy-in-AGI, physical bottlenecks)

**Garden ID:** `powpowpow`

**Emission rules:**
```python
if best_case_revenue < best_case_cost:
    emit_signal("unprofitability")
```

## UKGraph (UK economy sensor)

**Data:** `forests/ukgraph/data/planning/` (100 apps), `forests/ukgraph/data/contracts/` (100 contracts), `canonical/ukgraph/ashe_earnings.jsonl` (13,596 rows), `data/uk_hpi/uk_hpi_full.csv` (379 rows)

**Signals:**
- **Geo signal**: Planning applications hinting near-term electrical work
- **Ranking**: Planning workload mix (extensions vs conversions vs commercial vs new build)
- **Ranking**: Buyer concentration in contract spend
- **Ranking**: Fastest-rising UK pay by occupation (ASHE 2022-23)
- **Comparison**: UK house price divergence by property type

**Garden ID:** `ukgraph`

**Emission rules:**
```python
if matching_planning_apps > threshold:
    emit_signal("precursor_work")
if year_over_year_change > 10%:
    emit_signal("wage_momentum")
if type_spread > 2%:
    emit_signal("hpi_divergence")
```

## UKProducts (physical goods)

**Data:** `canonical/ukproducts/2026-09-19.jsonl` (107 rows: 100 product listings, 6 charity margins, 1 sold)

**Signals:**
- **Ranking**: Charity shop flip margins (buy price vs sell price, days to sell)

**Garden ID:** `ukproducts`

**Emission rules:**
```python
if margin_pct > 100:
    emit_signal("flip_opportunity")
```

## UKBoring (admin pain)

**Data:** `uk_boring/workflows/painful_tasks.py` (5 workflow definitions with cost, timeline, steps, receipt patterns)

**Signals:**
- **Ranking**: Admin tasks that punish delay hardest (parsed cost + timeline)

**Garden ID:** `boring`

**Emission rules:**
```python
rank_by(cost_gbp DESC, timeline_days DESC)
emit_signal("delay_penalty")
```

## Adding a garden

1. Add emitter function `_yourgarden_signals(limit)` in `mcp_server.py`
2. Add garden name to `signals_top` dispatch
3. Add to `_all_signals()` loop
4. Create channel profile in `channels/yourgarden.yaml`
5. Add to `_resolve_signal()` for content_from_signal support
