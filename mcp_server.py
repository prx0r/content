#!/usr/bin/env python3
"""content-sensor MCP server — agent-operated content factory (V1).

Same stdio shape as datagarden's MCP servers:
    python mcp_server.py                 # list tools
    python mcp_server.py <tool> '<json>' # call tool
    python mcp_server.py --serve         # MCP stdio server

V1 pipeline (brutally small):
    signals_top -> build_content -> render_video (+ render_narration)
    every video logged as signal_id -> video_id in store/lineage.jsonl

Truth contract: signals carry evidence (file + observed_at) and honest
confidence. Anything without backing data returns UNAVAILABLE, never
invented metrics. Hooks/beats are deterministic templates over signal
fields — the model phrases, it never discovers the fact.
"""

import hashlib
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).parent
STORE = ROOT / "store"
PROJECTS = STORE / "projects"
LINEAGE = STORE / "lineage.jsonl"

POW_CARDS = Path("/home/ubuntu/powpowpow/v1_live_cards.json")
UK_PLANNING = Path("/home/ubuntu/datagarden/forests/ukgraph/data/planning/2026-09-19.jsonl")
UK_CONTRACTS = Path("/home/ubuntu/datagarden/forests/ukgraph/data/contracts/2026-09-19.jsonl")

HF_TEMPLATE_DIR = ROOT / "hf-test"  # proven 9:16 brand composition
EDGE_TTS_BIN = ROOT / ".venv" / "bin" / "edge-tts"

for d in (STORE, PROJECTS):
    d.mkdir(parents=True, exist_ok=True)


def utcnow():
    return datetime.now(timezone.utc).isoformat()


def sig_id(*parts):
    return "sig_" + hashlib.sha1("|".join(parts).encode()).hexdigest()[:12]


# ============================================================
# SIGNAL EMISSION (deterministic transforms over on-disk data)
# ============================================================

def _pow_signals(limit):
    if not POW_CARDS.exists():
        return {"status": "UNAVAILABLE", "reason": "v1_live_cards.json missing"}
    cards = json.loads(POW_CARDS.read_text())
    observed = {c: cards[c].get("timestamp", "") for c in cards}
    signals = []
    best_net = {}
    excluded = []
    for coin, card in cards.items():
        hw = card.get("hardware", {})
        sane = {h: m for h, m in hw.items()
                if (m.get("revenue_usd_day") or 0) < 100_000}
        for h in hw:
            if h not in sane:
                excluded.append(f"{coin}/{h} revenue ${hw[h].get('revenue_usd_day'):,.0f}/day")
        if not sane:
            continue
        name = max(sane, key=lambda h: sane[h].get("net_profit_usd_day") or -1e18)
        m = sane[name]
        best_net[coin] = m.get("net_profit_usd_day")
        if (m.get("net_profit_usd_day") or 0) < 0:
            signals.append({
                "id": sig_id("pow", coin, "unprofitable"),
                "type": "anomaly",
                "title": f"No profitable hardware for {coin} at current prices",
                "claim": (f"Best case ({name}) nets "
                          f"${m['net_profit_usd_day']:.2f}/day after power and amortization."),
                "why": "Revenue per unit of compute is below marginal cost at current difficulty and price.",
                "entities": [coin, name],
                "metrics": [
                    {"name": "price_usd", "value": card.get("price_usd"), "unit": "USD"},
                    {"name": "revenue_usd_day", "value": m.get("revenue_usd_day"), "unit": "USD/day"},
                    {"name": "net_profit_usd_day", "value": m.get("net_profit_usd_day"), "unit": "USD/day"},
                ],
                "evidence": [{"file": str(POW_CARDS), "observed_at": observed.get(coin, "")}],
                "timespan": "point-in-time",
                "confidence": 0.9,
                "updated_at": utcnow(),
            })
    if best_net:
        ranked = sorted(best_net.items(), key=lambda kv: kv[1] or -1e18, reverse=True)
        signals.append({
            "id": sig_id("pow", "ranking", "best-net"),
            "type": "ranking",
            "title": "Least-unprofitable mineable asset right now",
            "claim": f"{ranked[0][0]} loses least at ${ranked[0][1]:.2f}/day best case.",
            "why": "Cross-asset best-net comparison at current prices and difficulty.",
            "entities": [c for c, _ in ranked],
            "metrics": [{"name": f"{c}_best_net_usd_day", "value": v, "unit": "USD/day"}
                        for c, v in ranked],
            "evidence": [{"file": str(POW_CARDS), "observed_at": max(observed.values())}],
            "timespan": "point-in-time",
            "confidence": 0.9,
            "notes": (f"Excluded implausible rigs: {'; '.join(excluded)}" if excluded else ""),
            "updated_at": utcnow(),
        })
    return {"status": "ok", "signals": signals[:limit]}


def _uk_signals(limit):
    signals = []
    if UK_PLANNING.exists():
        rows = [json.loads(l) for l in UK_PLANNING.read_text().splitlines() if l.strip()]
        kw = ("extension", "conversion", "commercial", "new build", "new-build")
        leads = [r for r in rows
                 if any(k in r.get("data", {}).get("description", "").lower() for k in kw)]
        refs = [r["data"].get("reference", "") for r in leads[:5]]
        signals.append({
            "id": sig_id("uk", "planning", "electrical-precursor"),
            "type": "geo_signal",
            "title": f"{len(leads)} of {len(rows)} recent planning applications hint near-term electrical work",
            "claim": (f"{len(leads)} applications mention extensions, conversions or "
                      f"commercial work that typically needs an electrician."),
            "why": "Approved front-end construction work precedes electrical fit-out demand.",
            "entities": ["electrician", "planning"],
            "metrics": [
                {"name": "matching_applications", "value": len(leads), "unit": "count"},
                {"name": "applications_scanned", "value": len(rows), "unit": "count"},
            ],
            "evidence": [{"file": str(UK_PLANNING), "refs": refs}],
            "timespan": "7d",
            "confidence": 0.5,
            "updated_at": utcnow(),
        })
    if UK_PLANNING.exists():
        rows = [json.loads(l) for l in UK_PLANNING.read_text().splitlines() if l.strip()]
        fams = {"extensions": ("extension", "infill"),
                "commercial": ("commercial", "office", "retail"),
                "conversions": ("conversion", "change of use"),
                "new_build": ("new build", "new-build", "dwellings")}
        counts = {}
        for fam, kws in fams.items():
            counts[fam] = sum(1 for r in rows if any(
                k in r.get("data", {}).get("description", "").lower() for k in kws))
        if sum(counts.values()) > 0:
            top = max(counts, key=counts.get)
            signals.append({
                "id": sig_id("uk", "planning", "workload-mix"),
                "type": "ranking",
                "title": f"Planning workload led by {top} ({counts[top]} of {len(rows)} applications)",
                "claim": ("Development mix: " + ", ".join(
                    f"{f.replace('_', ' ')} {c}" for f, c in sorted(counts.items(), key=lambda kv: -kv[1])) + "."),
                "why": "Workload mix previews which trades get pulled first.",
                "entities": ["planning"] + [f for f, c in counts.items() if c],
                "metrics": [{"name": f"{f}_applications", "value": c, "unit": "count"}
                            for f, c in counts.items()],
                "evidence": [{"file": str(UK_PLANNING)}],
                "timespan": "7d",
                "confidence": 0.7,
                "updated_at": utcnow(),
            })
    if UK_CONTRACTS.exists():
        rows = [json.loads(l) for l in UK_CONTRACTS.read_text().splitlines() if l.strip()]
        cons = [(r.get("data", {}).get("value_gbp", 0) or 0,
                 r.get("data", {}).get("contract_id", ""),
                 r.get("data", {}).get("title", "")) for r in rows]
        cons.sort(reverse=True)
        top = cons[:5]
        signals.append({
            "id": sig_id("uk", "contracts", "top-value"),
            "type": "ranking",
            "title": "Largest open contract values in the latest pull",
            "claim": f"Top contract at £{top[0][0]:,.0f}: {top[0][2][:80]}." if top else "No contracts.",
            "why": "Ranked by advertised value_gbp, latest contracts pull.",
            "entities": ["contracts"],
            "metrics": [{"name": "value_gbp", "value": v, "unit": "GBP"} for v, _, _ in top],
            "evidence": [{"file": str(UK_CONTRACTS), "contract_ids": [c for _, c, _ in top]}],
            "timespan": "7d",
            "confidence": 0.7,
            "updated_at": utcnow(),
        })
        buyers = {}
        for r in rows:
            d = r.get("data", {})
            b = d.get("buyer", "") or "unknown"
            buyers[b] = buyers.get(b, 0) + (d.get("value_gbp", 0) or 0)
        top_buyers = sorted(buyers.items(), key=lambda kv: -kv[1])[:3]
        if top_buyers and top_buyers[0][1] > 0:
            signals.append({
                "id": sig_id("uk", "contracts", "buyer-concentration"),
                "type": "ranking",
                "title": f"Contract spend concentrated: {top_buyers[0][0][:50]} leads at £{top_buyers[0][1]:,.0f}",
                "claim": ("Top buyers by advertised value: " + "; ".join(
                    f"{b[:40]} £{v:,.0f}" for b, v in top_buyers) + "."),
                "why": "Buyer concentration shows where public money routes.",
                "entities": ["contracts", "buyers"],
                "metrics": [{"name": "buyer_value_gbp", "value": v, "unit": "GBP"}
                            for _, v in top_buyers],
                "evidence": [{"file": str(UK_CONTRACTS)}],
                "timespan": "7d",
                "confidence": 0.6,
                "updated_at": utcnow(),
            })
    if not signals:
        return {"status": "UNAVAILABLE", "reason": "ukgraph planning/contracts data missing"}
    return {"status": "ok", "signals": signals[:limit]}


# interestingness = magnitude x confidence x novelty x relevance x actionability
_TYPE_WEIGHTS = {  # type -> (human_relevance, actionability)
    "anomaly": (0.9, 0.8),
    "ranking": (0.7, 0.7),
    "geo_signal": (0.8, 0.8),
    "change": (0.8, 0.7),
    "comparison": (0.7, 0.6),
    "causal": (0.8, 0.6),
    "concept": (0.8, 0.6),
    "thesis": (0.8, 0.7),
}

CONTENT_WORTHY_TYPES = ("anomaly", "ranking", "geo_signal", "change",
                        "comparison", "causal", "concept", "thesis")

UKPRODUCTS_CSV = Path("/home/ubuntu/datagarden/canonical/ukproducts/2026-09-19.jsonl")
ASHE_JSONL = Path("/home/ubuntu/datagarden/canonical/ukgraph/ashe_earnings.jsonl")
HPI_CSV = Path("/home/ubuntu/datagarden/data/uk_hpi/uk_hpi_full.csv")
PAINFUL_TASKS_PY = Path("/home/ubuntu/datagarden/uk_boring/workflows/painful_tasks.py")

POW_COINS_PY = Path("/home/ubuntu/powpowpow/coins.py")
POW_CATS_PY = Path("/home/ubuntu/powpowpow/categories.py")
THESES_YAML = ROOT / "registry" / "theses.yaml"

_POWREG = None


def _pow_registry():
    global _POWREG
    if _POWREG is None:
        import importlib.util
        spec = importlib.util.spec_from_file_location("pow_coins", str(POW_COINS_PY))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        cspec = importlib.util.spec_from_file_location("pow_cats", str(POW_CATS_PY))
        cmod = importlib.util.module_from_spec(cspec)
        cspec.loader.exec_module(cmod)
        _POWREG = (getattr(mod, "COINS", {}), getattr(cmod, "CATEGORIES", {}))
    return _POWREG


def _live_cards():
    try:
        return json.loads(POW_CARDS.read_text())
    except (OSError, ValueError):
        return {}


def _best_hw(card):
    hw = card.get("hardware", {}) or {}
    sane = {h: m for h, m in hw.items() if (m.get("revenue_usd_day") or 0) < 100_000}
    if not sane:
        return None, None
    name = max(sane, key=lambda h: sane[h].get("net_profit_usd_day") or -1e18)
    return name, sane[name]


def _coin_category(topic, cats):
    return [cid for cid, c in cats.items() if topic in c.get("coins", [])]


ANGLES = ("explain", "why-now", "economics", "hardware", "signal")


def _concept_signal(topic, angle):
    """Deterministic Concept signal from the powpowpow registry (+live cards)."""
    coins, cats = _pow_registry()
    topic = (topic or "").upper()
    angle = (angle or "explain").lower()
    if angle not in ANGLES:
        return {"status": "error",
                "reason": f"Unknown angle '{angle}'. Use one of {list(ANGLES)}."}
    if topic not in coins:
        return {"status": "error",
                "reason": f"Unknown topic '{topic}'. See concepts_top."}
    c = coins[topic]
    live = _live_cards().get(topic, {})
    evidence = [{"file": str(POW_COINS_PY)}, {"file": str(POW_CATS_PY)}]
    metrics = []
    chain = c.get("chain", {}) or {}
    if chain.get("max_supply"):
        metrics.append({"name": f"{topic.lower()}_max_supply",
                        "value": chain["max_supply"], "unit": "native"})
    if chain.get("emission_per_day"):
        metrics.append({"name": f"{topic.lower()}_emission_per_day",
                        "value": chain["emission_per_day"], "unit": "native/day"})
    name, desc, cons = c.get("name", topic), c.get("description", ""), c.get("consensus", "")
    cat_ids = _coin_category(topic, cats)
    cat_line = ""
    if cat_ids:
        cat_line = "; ".join(f"{cats[i].get('name', i)}: {cats[i].get('description', '')}"
                             for i in cat_ids)
    hw_name, hw = _best_hw(live)
    if live:
        evidence.append({"file": str(POW_CARDS),
                         "observed_at": live.get("timestamp", "")})
    if angle == "explain":
        claim = f"{name}: {desc} Consensus: {cons}."
        why = cat_line or "Tracked in the PowPowPow registry."
    elif angle == "signal":
        return {"status": "redirect", "garden": "powpowpow"}
    else:
        if not live or not hw:
            return {"status": "UNAVAILABLE",
                    "reason": f"No live economics for {topic} — collectors pending."}
        metrics.extend([
            {"name": "price_usd", "value": live.get("price_usd"), "unit": "USD"},
            {"name": "revenue_usd_day", "value": hw.get("revenue_usd_day"), "unit": "USD/day"},
            {"name": "net_profit_usd_day", "value": hw.get("net_profit_usd_day"), "unit": "USD/day"},
            {"name": "power_watts", "value": hw.get("power_watts"), "unit": "W"},
        ])
        if angle == "economics":
            claim = (f"{name} best case ({hw_name}) nets "
                     f"${hw.get('net_profit_usd_day'):.2f}/day.")
            why = "Revenue per unit of compute versus marginal cost at current difficulty and price."
        elif angle == "hardware":
            claim = (f"{name} best case runs {hw_name}: {hw.get('power_watts')}W, "
                     f"${hw.get('cost_usd'):,.0f} hardware.")
            why = "Hardware demand follows network growth; power draws show the physical footprint."
        else:  # why-now
            claim = (f"{name} best case nets ${hw.get('net_profit_usd_day'):.2f}/day "
                     f"at ${live.get('price_usd')} right now.")
            why = "Current difficulty and price make this the timely read."
    return {"status": "ok", "signal": {
        "id": f"con_{topic}_{angle}", "type": "concept", "garden": "powpowpow",
        "title": f"{name} — {angle}",
        "claim": claim, "why": why,
        "entities": [topic] + cat_ids,
        "metrics": [m for m in metrics if m.get("value") is not None],
        "evidence": evidence, "timespan": "evergreen" if angle == "explain" else "point-in-time",
        "confidence": 0.8 if angle == "explain" else 0.9,
        "updated_at": utcnow()}}


def _thesis_signals():
    import yaml
    doc = yaml.safe_load(THESES_YAML.read_text())
    out = []
    for t in doc.get("theses", []):
        out.append({"id": t["id"], "type": "thesis", "garden": "powpowpow",
                    "title": t["title"], "claim": t["claim"], "why": t.get("why", ""),
                    "entities": t.get("entities", []), "metrics": t.get("metrics", []),
                    "evidence": t.get("evidence", []), "timespan": "evergreen",
                    "confidence": t.get("confidence", 0.6), "updated_at": utcnow()})
    return out


def _relationship_signal(a, b):
    coins, cats = _pow_registry()
    a, b = (a or "").upper(), (b or "").upper()
    if a not in coins or b not in coins:
        return {"status": "error", "reason": "Both topics must come from concepts_top."}
    ca, cb = coins[a], coins[b]
    confrontation = (f"{ca.get('name')}: {ca.get('description', '')} "
                     f"({ca.get('consensus', '')}). {cb.get('name')}: "
                     f"{cb.get('description', '')} ({cb.get('consensus', '')}).")
    shared = set(_coin_category(a, cats)) & set(_coin_category(b, cats))
    why = ("Both track the same scarce resource." if shared
           else "Different scarce resources — different cost floors.")
    metrics = []
    for t, cc in ((a, ca), (b, cb)):
        ch = cc.get("chain", {}) or {}
        if ch.get("max_supply"):
            metrics.append({"name": f"{t.lower()}_max_supply",
                            "value": ch["max_supply"], "unit": "native"})
        if ch.get("emission_per_day"):
            metrics.append({"name": f"{t.lower()}_emission_per_day",
                            "value": ch["emission_per_day"], "unit": "native/day"})
    return {"status": "ok", "signal": {
        "id": f"rel_{a}_{b}", "type": "comparison", "garden": "powpowpow",
        "title": f"{ca.get('name')} vs {cb.get('name')} — how the approaches differ",
        "claim": confrontation, "why": why, "entities": [a, b],
        "metrics": metrics, "evidence": [{"file": str(POW_COINS_PY)}],
        "timespan": "evergreen", "confidence": 0.8, "updated_at": utcnow()}}


def _score_signal(s):
    mag = 0.5
    for m in s.get("metrics", []) or []:
        v = m.get("value")
        if isinstance(v, (int, float)):
            name = (m.get("name") or "").lower()
            unit = (m.get("unit") or "")
            if unit == "%" or "change" in name or "pressure" in name:
                mag = max(mag, min(abs(v) / 30.0, 1.0))
    rel, act = _TYPE_WEIGHTS.get(s.get("type"), (0.5, 0.5))
    conf = s.get("confidence", 0.5) or 0.5
    score = round(mag * conf * 1.0 * rel * act, 3)  # novelty = 1.0 on Day 0
    eligible = bool(s.get("metrics") and s.get("evidence")
                    and conf >= 0.5 and s.get("type") in CONTENT_WORTHY_TYPES)
    return score, eligible


def signals_top(garden="powpowpow", limit=10):
    """Deterministic candidate signals from on-disk garden data, scored."""
    garden = (garden or "").lower()
    try:
        limit = max(1, min(int(limit), 25))
    except (TypeError, ValueError):
        limit = 10
    if garden in ("pow", "powpowpow", "resources"):
        res = _pow_signals(limit)
    elif garden in ("uk", "ukgraph", "ukopportunity"):
        res = _uk_signals(limit)
    elif garden in ("ukproducts", "breadup", "products"):
        res = _products_signals(limit)
    elif garden in ("ashe", "wages"):
        res = _ashe_signals(limit)
    elif garden in ("hpi", "house", "housing"):
        res = _hpi_signals(limit)
    elif garden in ("boring", "ukboring", "admin"):
        res = _boring_signals(limit)
    else:
        return {"status": "error",
                "reason": f"Unknown garden '{garden}'. Use powpowpow | ukgraph | ukproducts | ashe | hpi | boring."}
    if res.get("status") == "ok":
        for s in res["signals"]:
            s["score"], s["eligible"] = _score_signal(s)
        res["signals"].sort(key=lambda s: s.get("score", 0), reverse=True)
    return res


def _products_signals(limit):
    if not UKPRODUCTS_CSV.exists():
        return {"status": "UNAVAILABLE", "reason": "ukproducts canonical missing"}
    rows = [json.loads(l) for l in UKPRODUCTS_CSV.read_text().splitlines() if l.strip()]
    flips = [r for r in rows if r.get("metric") == "charity_shop_margin"]
    signals = []
    if flips:
        top = max(flips, key=lambda r: r.get("value", {}).get("margin_pct", 0) or 0)
        v = top.get("value", {})
        signals.append({
            "id": sig_id("products", "flip", str(v.get("brand", ""))),
            "type": "ranking",
            "title": (f"Charity flip: {v.get('brand')} bought £{v.get('buy_price_gbp')} "
                      f"sold £{v.get('sell_price_gbp')} in {v.get('days_to_sell')} days"),
            "claim": (f"{v.get('brand')}: buy £{v.get('buy_price_gbp')}, "
                      f"sell £{v.get('sell_price_gbp')} ({v.get('margin_pct')}% margin, "
                      f"{v.get('days_to_sell')} days on {v.get('platform')})."),
            "why": "Second-hand spreads persist where sourcing skill beats listing skill.",
            "entities": [str(v.get("brand", "")).lower(), "flip", str(v.get("platform", ""))],
            "metrics": [
                {"name": "margin_pct", "value": v.get("margin_pct"), "unit": "%"},
                {"name": "days_to_sell", "value": v.get("days_to_sell"), "unit": "days"},
                {"name": "buy_price_gbp", "value": v.get("buy_price_gbp"), "unit": "GBP"},
                {"name": "sell_price_gbp", "value": v.get("sell_price_gbp"), "unit": "GBP"},
            ],
            "evidence": [{"file": str(UKPRODUCTS_CSV),
                          "observation_id": top.get("observation_id", "")}],
            "timespan": "30d",
            "confidence": 0.6,
            "updated_at": utcnow(),
        })
    if not signals:
        return {"status": "UNAVAILABLE", "reason": "no flip margins computed yet"}
    return {"status": "ok", "signals": signals[:limit]}


def _ashe_signals(limit):
    if not ASHE_JSONL.exists():
        return {"status": "UNAVAILABLE", "reason": "ashe canonical missing"}
    by_occ = {}
    for l in ASHE_JSONL.read_text().splitlines():
        if not l.strip():
            continue
        r = json.loads(l)
        v = r.get("value", {})
        pay = v.get("median_annual_pay")
        if not pay:
            continue
        by_occ.setdefault((v.get("occupation_code"), v.get("occupation_name")),
                          {}).setdefault(v.get("year"), []).append(pay)
    import statistics
    changes = []
    for (code, name), years in by_occ.items():
        if 2022 in years and 2023 in years:
            m22 = statistics.median(years[2022])
            m23 = statistics.median(years[2023])
            if m22 > 0:
                changes.append(((m23 - m22) / m22 * 100, name, code, m22, m23))
    if not changes:
        return {"status": "UNAVAILABLE", "reason": "no overlapping years"}
    changes.sort(reverse=True)
    top = changes[:5]
    champ = top[0]
    return {"status": "ok", "signals": [{
        "id": sig_id("ashe", "pay-risers-2023"),
        "type": "ranking",
        "title": f"Fastest-rising UK pay 2022-23: {champ[1]} up {champ[0]:.0f}%",
        "claim": ("Biggest median-pay rises: " + "; ".join(
            f"{n} +{p:.0f}% (£{a:,.0f}→£{b:,.0f})" for p, n, c, a, b in top) + "."),
        "why": "Pay momentum reveals scarcity before vacancy data confirms it.",
        "entities": ["wages", "ashe", "2023"],
        "metrics": [{"name": "pay_change_pct", "value": round(p, 1), "unit": "%"}
                    for p, n, c, a, b in top],
        "evidence": [{"file": str(ASHE_JSONL)}],
        "timespan": "12m",
        "confidence": 0.8,
        "updated_at": utcnow(),
    }][:limit]}


def _hpi_signals(limit):
    if not HPI_CSV.exists():
        return {"status": "UNAVAILABLE", "reason": "hpi csv missing"}
    import csv
    rows = list(csv.DictReader(open(HPI_CSV)))
    rows = [r for r in rows if r.get("Name") == "United Kingdom" and r.get("Period")]
    if not rows:
        return {"status": "UNAVAILABLE", "reason": "no UK rows"}
    latest = max(rows, key=lambda r: r["Period"])
    types = ["All property types", "Detached houses", "Semi-detached houses",
             "Terraced houses", "Flats and maisonettes", "New build"]
    vals = []
    for t in types:
        try:
            y = float((latest.get(f"Percentage change (yearly) {t}") or "").strip() or "nan")
            p = latest.get(f"Average price {t}", "").strip().replace(",", "")
            price = float(p) if p else None
        except ValueError:
            continue
        if y == y and price:
            vals.append((y, t, price))
    if not vals:
        return {"status": "UNAVAILABLE", "reason": "no priced rows"}
    vals.sort(reverse=True)
    spread = vals[0][0] - vals[-1][0]
    return {"status": "ok", "signals": [{
        "id": sig_id("hpi", "divergence", latest["Period"]),
        "type": "comparison",
        "title": (f"UK house prices split: {vals[0][1]} {vals[0][0]:+.1f}% YoY vs "
                  f"{vals[-1][1]} {vals[-1][0]:+.1f}% ({latest['Period']})"),
        "claim": ("Yearly change by type: " + "; ".join(
            f"{t} {y:+.1f}% (£{p:,.0f})" for y, t, p in vals) + "."),
        "why": "Type divergence shows which segments still move and which stall.",
        "entities": ["house prices", "uk", latest["Period"]],
        "metrics": [{"name": "yoy_change_pct", "value": round(y, 1), "unit": "%"}
                    for y, t, p in vals[:4]],
        "evidence": [{"file": str(HPI_CSV), "period": latest["Period"]}],
        "timespan": "12m",
        "confidence": 0.85,
        "updated_at": utcnow(),
    }][:limit]}


def _boring_signals(limit):
    if not PAINFUL_TASKS_PY.exists():
        return {"status": "UNAVAILABLE", "reason": "painful tasks missing"}
    import importlib.util
    import re
    spec = importlib.util.spec_from_file_location("painful", str(PAINFUL_TASKS_PY))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    tasks = [v for k, v in vars(mod).items()
             if type(v).__name__ == "PainfulTask"]
    if not tasks:
        return {"status": "UNAVAILABLE", "reason": "no tasks defined"}

    def gbp(s):
        m = re.search(r"£([\d.]+)", s or "")
        return float(m.group(1)) if m else None

    def days(s):
        m = re.findall(r"(\d+)\s*weeks?", s or "")
        return max(map(int, m)) * 7 if m else None

    ranked = []
    for t in tasks:
        c, d = gbp(t.cost), days(t.timeline)
        if c is None and d is None:
            continue
        ranked.append((d or 0, c or 0, t))
    if not ranked:
        return {"status": "UNAVAILABLE", "reason": "no parseable penalties"}
    ranked.sort(reverse=True)
    top = ranked[:4]
    champ = top[0][2]
    champ_days, champ_cost = top[0][0], top[0][1]
    return {"status": "ok", "signals": [{
        "id": sig_id("boring", "penalties"),
        "type": "ranking",
        "title": f"UK admin that punishes delay hardest: {champ.name}",
        "claim": ("Worst delay penalties: " + "; ".join(
            f"{t.name}: {t.cost} ({t.timeline})" for _, _, t in top) + "."),
        "why": "Slow admin has a price; doing it late costs more than doing it now.",
        "entities": ["uk admin", "delay"],
        "metrics": ([{"name": "timeline_days", "value": champ_days, "unit": "days"}]
                    if champ_days else [])
        + [{"name": "cost_gbp", "value": c, "unit": "GBP"} for _, c, _ in top if c],
        "evidence": [{"file": str(PAINFUL_TASKS_PY),
                      "workflow_ids": [t.workflow_id for _, _, t in top]}],
        "timespan": "evergreen",
        "confidence": 0.7,
        "updated_at": utcnow(),
    }][:limit]}


def _all_signals():
    out = []
    for garden in ("powpowpow", "ukgraph", "ukproducts", "ashe", "hpi", "boring"):
        r = signals_top(garden, 25)
        if r.get("status") == "ok":
            for s in r["signals"]:
                s = dict(s)
                s["garden"] = garden
                out.append(s)
    return out


def _resolve_signal(sid):
    """Garden signals, Concept (con_TOPIC_angle), thesis (the_slug), rel (rel_A_B)."""
    if not sid:
        return None
    for s in _all_signals():
        if s["id"] == sid:
            return s
    if sid.startswith("con_"):
        try:
            topic, angle = sid[4:].rsplit("_", 1)
        except ValueError:
            return None
        r = _concept_signal(topic, angle)
        if r.get("status") != "ok" or "signal" not in r:
            return None
        s = r["signal"]
        s["score"], s["eligible"] = _score_signal(s)
        return s
    if sid.startswith("rel_"):
        parts = sid[4:].split("_")
        if len(parts) != 2:
            return None
        r = _relationship_signal(parts[0], parts[1])
        if r.get("status") != "ok":
            return None
        s = r["signal"]
        s["score"], s["eligible"] = _score_signal(s)
        return s
    if sid.startswith("the_"):
        for s in _thesis_signals():
            if s["id"] == sid:
                s = dict(s)
                s["score"], s["eligible"] = _score_signal(s)
                return s
    return None


def expand_signal(signal_id=None):
    """Seed signal -> supporting graph neighbourhood (2-4 strongest facts)."""
    if not signal_id:
        return {"status": "error", "reason": "Pass signal_id from signals_top."}
    alls = _all_signals()
    seed = _resolve_signal(signal_id)
    if not seed:
        return {"status": "error", "reason": f"Unknown signal_id '{signal_id}'."}
    supporting = [s for s in alls
                  if s["id"] != signal_id and s["garden"] == seed["garden"]]
    supporting.sort(key=lambda s: s.get("score", 0), reverse=True)
    supporting = supporting[:3]
    return {"status": "ok", "seed": seed, "supporting": supporting,
            "facts": [seed.get("claim", "")] + [s.get("claim", "") for s in supporting]}


# ============================================================
# CONTENT (deterministic template over a signal — no discovery)
# ============================================================

TEMPLATE_FOR_TYPE = {
    "anomaly": "anomaly",
    "ranking": "ranking",
    "comparison": "vs",
    "change": "what_changed",
    "geo_signal": "map",
    "causal": "why",
    "concept": "explainer",
    "thesis": "why",
}

TEMPLATES = {
    "anomaly": {"beats": 3, "use": "one surprising measurement + evidence"},
    "ranking": {"beats": 3, "use": "ordered list, winner first"},
    "vs": {"beats": 3, "use": "A vs B comparison"},
    "what_changed": {"beats": 3, "use": "before/after change"},
    "map": {"beats": 3, "use": "place-anchored precursor signal"},
    "why": {"beats": 3, "use": "causal chain in plain words"},
    "opportunity": {"beats": 4, "use": "what someone can do because of this"},
    "explainer": {"beats": 4, "use": "what it is, why it matters, what connects"},
}

QUERIES = {
    "EXPLAIN": ("explainer", "What {entities} actually is."),
    "CHANGE": ("what_changed", "What changed: {title}"),
    "WHY": ("why", "Why: {title}"),
    "WHERE": ("map", "Where it's strongest: {title}"),
    "COMPARE": ("vs", "{entities} head to head."),
    "OPPORTUNITY": ("opportunity", "What you can do about {entities}."),
    "WARNING": ("anomaly", "Who's exposed: {title}"),
}


def list_templates():
    """Template catalogue: signal.type -> template mapping."""
    return {"status": "ok", "default_by_type": TEMPLATE_FOR_TYPE, "templates": TEMPLATES}


def _hook_for(signal, template):
    ents = ", ".join(signal.get("entities", [])[:2])
    if template == "anomaly":
        return f"Something strange is happening to {ents}."
    if template == "ranking":
        return f"Ranked: {signal.get('title', '')}"
    if template == "vs":
        return f"{ents}: head to head."
    if template == "what_changed":
        return f"What changed: {signal.get('title', '')}"
    if template == "map":
        return f"On the map: {signal.get('title', '')}"
    if template == "opportunity":
        ents = ", ".join(signal.get("entities", [])[:2])
        return f"What you can do about {ents}."
    if template == "explainer":
        ents = ", ".join(signal.get("entities", [])[:2])
        return f"What {ents} actually is."
    return f"Why: {signal.get('title', '')}"


def content_from_signal(signal_id=None, query="CHANGE"):
    """Seed signal -> query expansion -> render manifest (hook/claim/proof/close)."""
    query = (query or "CHANGE").upper()
    if query not in QUERIES:
        return {"status": "error",
                "reason": f"Unknown query '{query}'. Use one of {sorted(QUERIES)}."}
    exp = expand_signal(signal_id)
    if exp.get("status") != "ok":
        return exp
    seed, supporting = exp["seed"], exp["supporting"]
    if not seed.get("eligible", True):
        return {"status": "error",
                "reason": "Signal fails the content-worthiness gate (needs metrics + evidence)."}
    template, hook_t = QUERIES[query]
    hook = hook_t.format(title=seed.get("title", ""),
                         entities=", ".join(seed.get("entities", [])[:2]))
    proof = []
    if seed.get("metrics"):
        m = seed["metrics"][0]
        proof.append(f"{m['name']}: {m['value']} {m.get('unit', '')}".strip())
    supporting_claims = [s["claim"] for s in supporting[:3] if s.get("claim")]
    proof.extend(supporting_claims)
    proof = proof[:4]
    close = seed.get("why", "")
    beats = [seed.get("claim", "")] + proof[1:3]
    if close:
        beats.append(close)
    content = {
        "signal_id": seed["id"],
        "query": query,
        "template": template,
        "hook": hook,
        "claim": seed.get("claim", ""),
        "proof": proof,
        "close": close,
        "source_ids": [seed["id"]] + [s["id"] for s in supporting],
        "beats": beats[:4],
        "supporting_claims": supporting_claims,
        "source_label": f"{seed.get('entities', ['garden'])[0]} · Sep 2026",
        "metrics": seed.get("metrics", []),
        "evidence": seed.get("evidence", []),
        "created_at": utcnow(),
    }
    cid = "content_" + seed["id"].replace("sig_", "") + "_" + query.lower()
    path = STORE / f"{cid}.json"
    path.write_text(json.dumps(content, indent=2))
    return {"status": "ok", "content_id": cid, "path": str(path), "content": content}


def build_content(signal=None, template=None):
    """Signal JSON -> content.json (hook + beats + source label)."""
    if not isinstance(signal, dict) or not signal.get("id"):
        return {"status": "error", "reason": "Pass a full signal object from signals_top."}
    if not signal.get("metrics"):
        return {"status": "error", "reason": "Signal has no metrics — refusing to render vibes."}
    template = template or TEMPLATE_FOR_TYPE.get(signal.get("type"), "anomaly")
    if template not in TEMPLATES:
        return {"status": "error",
                "reason": f"Unknown template '{template}'. See list_templates."}
    beats = [signal.get("claim", "")]
    for m in signal.get("metrics", [])[:2]:
        beats.append(f"{m['name']}: {m['value']} {m.get('unit', '')}".strip())
    if signal.get("why"):
        beats.append(signal["why"])
    content = {
        "signal_id": signal["id"],
        "query": "DIRECT",
        "template": template,
        "hook": _hook_for(signal, template),
        "claim": signal.get("claim", ""),
        "proof": beats[1:4],
        "close": signal.get("why", ""),
        "source_ids": [signal["id"]],
        "beats": beats[:4],
        "source_label": f"{signal.get('entities', ['garden'])[0]} · Sep 2026",
        "metrics": signal.get("metrics", []),
        "evidence": signal.get("evidence", []),
        "created_at": utcnow(),
    }
    cid = "content_" + signal["id"].replace("sig_", "")
    path = STORE / f"{cid}.json"
    path.write_text(json.dumps(content, indent=2))
    return {"status": "ok", "content_id": cid, "path": str(path), "content": content}


# ============================================================
# RENDER (content.json -> HyperFrames 9:16 MP4, lineage logged)
# ============================================================

BRAND_DIR = ROOT / "brand"


def _mix_audio(narration, out):
    """Narration over looped bed (ducked) + sting head + whoosh transition."""
    sting, whoosh, bed = (BRAND_DIR / "sting.wav", BRAND_DIR / "whoosh.wav",
                          BRAND_DIR / "bed.wav")
    if not (sting.exists() and whoosh.exists() and bed.exists()):
        return None
    nar_dur = _media_duration(narration)
    total = nar_dur + 1.2
    r = subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-i", str(narration),
         "-stream_loop", "-1", "-i", str(bed), "-i", str(sting), "-i", str(whoosh),
         "-filter_complex",
         "[0:a]adelay=800|800,volume=1.0[narr];"
         "[1:a]volume=0.35,aloop=loop=-1:size=352800[bedl];"
         "[bedl][narr]sidechaincompress=threshold=0.02:ratio=8:attack=20:release=500[duck];"
         "[3:a]adelay=900|900,volume=0.5[wh];"
         "[duck][2:a][wh]amix=inputs=3:duration=first:dropout_transition=0,"
         f"atrim=0:{total:.1f}",
         "-t", f"{total:.1f}", str(out)],
        capture_output=True, text=True, timeout=180)
    return str(out) if r.returncode == 0 and out.exists() else None


def _media_duration(path):
    try:
        r = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                            "stream=duration", "-of", "csv=p=0", str(path)],
                           capture_output=True, text=True, timeout=30)
        vals = [float(x) for x in r.stdout.split() if x.strip()]
        return max(vals) if vals else 0.0
    except (OSError, ValueError):
        return 0.0


def _fill_anomaly_html(content, duration=8, audio_src=None):
    sig_title = content.get("hook", "")
    metrics = content.get("metrics", []) or [{}]
    m0 = metrics[0]
    big = m0.get("value", "?")
    name = str(m0.get("name", "")).lower()
    unit = str(m0.get("unit", ""))
    signed = unit == "%" or any(k in name for k in ("change", "pressure", "net", "delta"))

    def _human(v):
        a = abs(v)
        if a >= 1e9:
            return f"{v / 1e9:.0f}B"
        if a >= 1e6:
            return f"{v / 1e6:.0f}M"
        if a >= 1e3:
            return f"{v / 1e3:.0f}K"
        return f"{v:,.0f}"

    try:
        v = float(big)
        if unit.lower() == "count":
            big = _human(v)
        else:
            big = (f"{v:+.0f}\u00a0{unit}" if signed else f"{_human(v)}\u00a0{unit}").strip()
    except (TypeError, ValueError):
        big = f"{big} {unit}".strip()
    label = m0.get("name", "").replace("_", " ")
    kicker = sig_title if len(sig_title) <= 110 else sig_title[:107] + "…"
    metric_size = 200 if len(big) <= 8 else (140 if len(big) <= 12 else 96)
    beats = content.get("beats", [])
    evidence = (beats[0] if beats else "") + (
        f" · {content.get('source_label', '')}" if content.get("source_label") else "")
    if audio_src:
        audio_tag = (f'<audio id="narration" class="clip" data-start="0" '
                     f'data-duration="{duration}" '
                     f'data-track-index="2" src="{audio_src}"></audio>')
    else:
        audio_tag = ""
    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=1080, height=1920" />
    <script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
    <style>
      * {{ margin: 0; padding: 0; box-sizing: border-box; }}
      html, body {{ margin: 0; width: 1080px; height: 1920px;
        overflow: hidden; background: #050505; }}
      #root {{ width: 100%; height: 100%; display: flex; flex-direction: column;
        justify-content: center; align-items: flex-start; padding: 120px 96px;
        font-family: Inter, ui-sans-serif, system-ui, sans-serif;
        background: #050505; color: #f7f7f5; transform-origin: center center; }}
      .kicker {{ color: #ffb224; font-size: 40px; font-weight: 700;
        letter-spacing: 0.12em; text-transform: uppercase; }}
      #metric {{ font-size: 200px; font-weight: 800; line-height: 1.05;
        letter-spacing: -0.04em; color: #f7f7f5; margin: 32px 0 8px; }}
      #label {{ font-size: 52px; font-weight: 500; color: #f7f7f5; }}
      #evidence {{ margin-top: 48px; font-size: 36px; color: #777;
        border-left: 6px solid #ffb224; padding-left: 28px; }}
    </style>
  </head>
  <body>
    <div id="root" data-composition-id="main" data-start="0"
         data-duration="{duration}" data-width="1080" data-height="1920">
      <div class="kicker" id="kicker">{kicker}</div>
      <div id="metric" style="font-size:{metric_size}px">{big}</div>
      <div id="label">{label}</div>
      <div id="evidence">{evidence}</div>
      {audio_tag}
    </div>
    <script>
      var DUR = {duration};
      var tl = gsap.timeline({{ paused: true }});
      tl.fromTo("#root", {{ scale: 1 }}, {{ scale: 1.04, duration: DUR, ease: "none" }}, 0);
      tl.from("#kicker", {{ opacity: 0, y: 24, duration: 0.5 }}, 0);
      tl.from("#metric", {{ opacity: 0, y: 40, duration: 0.8 }}, 0.3);
      tl.from("#label", {{ opacity: 0, y: 24, duration: 0.5 }}, 0.7);
      tl.from("#evidence", {{ opacity: 0, x: -24, duration: 0.5 }}, 1.1);
      window.__timelines = window.__timelines || {{}};
      window.__timelines["main"] = tl;
      tl.seek(0);
    </script>
  </body>
</html>
"""


def render_video(content_id=None, with_audio=True):
    """Render a built content.json to vertical MP4 via HyperFrames.

    With_audio mixes the narration track in at render time; the video
    runs as long as the narration needs (motion holds on the end card).
    """
    if not content_id:
        return {"status": "error", "reason": "Pass content_id from build_content."}
    src = STORE / f"{content_id}.json"
    if not src.exists():
        return {"status": "error", "reason": f"Unknown content_id '{content_id}'."}
    content = json.loads(src.read_text())
    if shutil.which("npx") is None:
        return {"status": "UNAVAILABLE", "reason": "npx not on PATH."}

    proj = PROJECTS / content_id
    proj.mkdir(parents=True, exist_ok=True)
    (proj / "hyperframes.json").write_text((HF_TEMPLATE_DIR / "hyperframes.json").read_text())
    (proj / "meta.json").write_text(json.dumps({"id": content_id, "name": content_id}))
    pkg = json.loads((HF_TEMPLATE_DIR / "package.json").read_text())
    pkg["name"] = content_id
    (proj / "package.json").write_text(json.dumps(pkg, indent=2))
    duration, audio_src = 8, None
    nar = STORE / f"{content_id}.narration.mp3"
    if with_audio and nar.exists():
        mix = STORE / f"{content_id}.mix.mp3"
        mixed = _mix_audio(nar, mix) if BRAND_DIR.exists() else None
        track = Path(mixed) if mixed else nar
        shutil.copy(track, proj / "narration.mp3")
        duration = max(8, int(_media_duration(track) + 1.5))
        audio_src = "narration.mp3"
    (proj / "index.html").write_text(
        _fill_anomaly_html(content, duration=duration, audio_src=audio_src))

    chk = subprocess.run(["npx", "--yes", "hyperframes@0.8.50", "check"],
                         cwd=proj, capture_output=True, text=True, timeout=180)
    if chk.returncode != 0:
        return {"status": "error", "reason": "hyperframes check failed",
                "detail": (chk.stdout + chk.stderr)[-2000:]}

    rnd = subprocess.run(["npx", "--yes", "hyperframes@0.8.50", "render",
                          "--low-memory-mode"],
                         cwd=proj, capture_output=True, text=True, timeout=900)
    for work in (proj / "renders").glob("work-*"):
        try:
            shutil.rmtree(work, ignore_errors=True)
        except OSError:
            pass
    mp4s = sorted((proj / "renders").glob("*.mp4")) if (proj / "renders").exists() else []
    if rnd.returncode != 0 or not mp4s:
        return {"status": "error", "reason": "hyperframes render failed",
                "detail": (rnd.stdout + rnd.stderr)[-2000:]}
    mp4 = max(mp4s, key=lambda p: p.stat().st_mtime)
    video_id = "vid_" + hashlib.sha1(f"{content_id}|{mp4.stat().st_mtime}".encode()).hexdigest()[:12]
    with open(LINEAGE, "a") as f:
        f.write(json.dumps({"signal_id": content.get("signal_id"), "content_id": content_id,
                            "video_id": video_id, "mp4": str(mp4),
                            "rendered_at": utcnow()}) + "\n")
    return {"status": "ok", "content_id": content_id, "video_id": video_id,
            "mp4": str(mp4), "signal_id": content.get("signal_id")}


# ============================================================
# NARRATION ($0 Edge TTS — proven path; Supertonic later)
# ============================================================

def render_narration(content_id=None, voice="en-US-AndrewMultilingualNeural"):
    """Content beats -> narration WAV via local Edge TTS ($0, no key)."""
    if not content_id:
        return {"status": "error", "reason": "Pass content_id from build_content."}
    src = STORE / f"{content_id}.json"
    if not src.exists():
        return {"status": "error", "reason": f"Unknown content_id '{content_id}'."}
    if not EDGE_TTS_BIN.exists():
        return {"status": "UNAVAILABLE", "reason": "edge-tts not installed in content/.venv."}
    content = json.loads(src.read_text())
    text = content.get("hook", "") + " " + " ".join(content.get("beats", []))
    out = STORE / f"{content_id}.narration.mp3"
    r = subprocess.run([str(EDGE_TTS_BIN), "--voice", voice, "--rate=+20%",
                        "--text", text, "--write-media", str(out)],
                       capture_output=True, text=True, timeout=180)
    if r.returncode != 0 or not out.exists():
        return {"status": "error", "reason": "edge-tts failed",
                "detail": (r.stdout + r.stderr)[-1000:]}
    return {"status": "ok", "content_id": content_id, "audio": str(out),
            "bytes": out.stat().st_size,
            "duration_s": _media_duration(out)}


# ============================================================
# STATUS + LINEAGE
# ============================================================

JEV_OPENROUTER_URL = "https://openrouter.ai/api/alpha/decisions"
JEV_OPENROUTER_MODEL = "typesafe/jev-1.13"
JEV_TYPESAFE_URL = "https://api.typesafe.ai/v1/systemone"
JEV_TYPESAFE_MODEL = "jev-latest"
JEV_RETRY_STATUSES = frozenset({408, 429, 500, 502, 503, 504})

FRAME_CHOICES = ("job_stress", "retraining", "opportunity", "geographic", "ignore")
TEMPLATE_CHOICES = ("anomaly", "ranking", "vs", "what_changed", "map", "why",
                    "opportunity", "explainer", "ignore")


def concepts_top():
    """Available Concept topics from the powpowpow registry + angles."""
    coins, cats = _pow_registry()
    topics = []
    for t in sorted(coins):
        c = coins[t]
        topics.append({"topic": t, "name": c.get("name", t),
                       "description": c.get("description", ""),
                       "consensus": c.get("consensus", ""),
                       "angles": list(ANGLES)})
    return {"status": "ok", "topics": topics,
            "categories": [{"id": i, "name": c.get("name", i),
                            "coins": c.get("coins", [])} for i, c in cats.items()]}


def concept_explain(topic=None, angle="explain"):
    """Concept -> proof + gated content (EXPLAIN query). Analytical framing only."""
    angle = (angle or "explain").lower()
    coins, _ = _pow_registry()
    if (topic or "").upper() not in coins:
        return {"status": "error",
                "reason": f"Unknown topic '{topic}'. See concepts_top."}
    if angle == "signal":
        for s in _all_signals():
            if s.get("garden") == "powpowpow" and (topic or "").upper() in s.get("entities", []) \
                    and s.get("type") == "anomaly":
                return {"status": "ok", "redirect": s["id"],
                        "note": "Live anomaly exists — use content_from_signal on it."}
        return {"status": "UNAVAILABLE",
                "reason": f"No live anomaly for {topic} right now."}
    sid = f"con_{(topic or '').upper()}_{angle}"
    seed = _resolve_signal(sid)
    if not seed:
        return {"status": "UNAVAILABLE",
                "reason": f"Cannot build {angle} for {topic} (no backing data)."}
    ing = ingest(sid)
    if ing.get("status") != "ok":
        return ing
    comp = compile(ing["proof"]["proof_id"], "EXPLAIN")
    return {"status": comp.get("status", "error"),
            "proof": ing["proof"], "content": comp.get("content"),
            "content_id": comp.get("content_id"),
            "gates": comp.get("gates"),
            "compile_receipt_id": comp.get("compile_receipt_id")}


def relationships(a=None, b=None):
    """Two topics -> analytical comparison (how approaches differ, never buy/sell)."""
    r = _relationship_signal(a, b)
    if r.get("status") != "ok":
        return r
    seed = r["signal"]
    seed["score"], seed["eligible"] = _score_signal(seed)
    ing = ingest(seed["id"])
    if ing.get("status") != "ok":
        return ing
    comp = compile(ing["proof"]["proof_id"], "COMPARE")
    return {"status": comp.get("status", "error"),
            "proof": ing["proof"], "content": comp.get("content"),
            "content_id": comp.get("content_id"),
            "gates": comp.get("gates"),
            "compile_receipt_id": comp.get("compile_receipt_id")}


def theses_top():
    """Curated analytical theses (evergreen, evidence-linked)."""
    out = []
    for s in _thesis_signals():
        s = dict(s)
        s["score"], s["eligible"] = _score_signal(s)
        out.append(s)
    out.sort(key=lambda s: s.get("score", 0), reverse=True)
    return {"status": "ok", "theses": out}


def _jev_provider():
    if os.environ.get("TYPESAFE_API_KEY"):
        return {"name": "typesafe", "endpoint": JEV_TYPESAFE_URL,
                "model": JEV_TYPESAFE_MODEL, "key": os.environ["TYPESAFE_API_KEY"]}
    if os.environ.get("OPENROUTER_API_KEY"):
        return {"name": "openrouter", "endpoint": JEV_OPENROUTER_URL,
                "model": JEV_OPENROUTER_MODEL, "key": os.environ["OPENROUTER_API_KEY"]}
    return None


def _router_questions(signal):
    ents = ", ".join(signal.get("entities", [])[:3])
    return {
        "interest": {
            "type": "score",
            "instructions": ("How materially interesting is this signal as a 20-second "
                             "evidence-driven video?"),
            "criteria": [
                "Routine graph update; no surprise, no money on the line.",
                "Notable change worth a mention alongside bigger stories.",
                "Must-cover economic change; surprising and actionable.",
            ],
        },
        "frame": {
            "type": "choice",
            "instructions": f"Which framing fits this signal about {ents}?",
            "criteria": {
                "job_stress": "occupation under pressure or displacement",
                "retraining": "implies a move someone should make",
                "opportunity": "actionable way to earn or save",
                "geographic": "place disparity is the story",
                "ignore": "not worth covering",
            },
        },
        "monetary": {
            "type": "noul",
            "instructions": "Is there an actionable monetary implication for a viewer?",
        },
        "template": {
            "type": "choice",
            "instructions": "Which render template fits?",
            "criteria": {t: t for t in TEMPLATE_CHOICES},
        },
    }


def _jev_ask(state, questions):
    """POST state+questions to the configured Jev provider (stdlib only)."""
    import time
    import urllib.error
    import urllib.request
    prov = _jev_provider()
    payload = {"model": prov["model"], "state": state, "questions": questions}
    body = json.dumps(payload).encode()
    last_err = "unknown"
    for attempt in range(3):
        req = urllib.request.Request(
            prov["endpoint"], data=body,
            headers={"Authorization": f"Bearer {prov['key']}",
                     "Content-Type": "application/json",
                     "HTTP-Referer": "https://github.com/prx0r/content",
                     "X-Title": "content-sensor"},
            method="POST")
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                return {"status": "ok", "origin": f"jev:{prov['name']}",
                        "answers": json.loads(resp.read().decode())}
        except urllib.error.HTTPError as e:
            last_err = f"HTTP {e.code}: {e.read().decode()[:300]}"
            if e.code not in JEV_RETRY_STATUSES:
                break
        except OSError as e:
            last_err = f"network: {e}"
        time.sleep(0.5 * (2 ** attempt))
    return {"status": "error", "origin": f"jev:{prov['name']}",
            "reason": f"provider failed: {last_err}"}


def _deterministic_verdict(signal):
    score = signal.get("score", 0.5) or 0.5
    frame = {"anomaly": "job_stress", "ranking": "opportunity",
             "geo_signal": "geographic", "change": "job_stress",
             "comparison": "opportunity", "causal": "retraining"}.get(
                 signal.get("type"), "ignore")
    text = json.dumps(signal).lower()
    monetary = any(k in text for k in ("gbp", "usd", "wage", "value", "profit", "earn", "cost"))
    return {"interest": round(score * 10, 1), "frame": frame,
            "monetary": monetary,
            "template": TEMPLATE_FOR_TYPE.get(signal.get("type"), "anomaly"),
            "probabilities": None}


def _parse_jev_answers(raw):
    """Extract verdict fields. Live shape: {answers: {q: {type,...}}}.
    Score rubrics return 0..N (N = len(criteria)-1); normalized to 0-10."""
    out = {"interest": None, "frame": None, "monetary": None,
           "template": None, "probabilities": {}}
    if not isinstance(raw, dict):
        return out
    ans = raw.get("answers", raw) or {}
    if not isinstance(ans, dict):
        return out
    iq = ans.get("interest", {}) or {}
    if isinstance(iq.get("score"), (int, float)):
        try:
            top = max(int(k) for k in (iq.get("legend") or {"2": 0}))
        except (ValueError, TypeError):
            top = 2
        out["interest"] = round(iq["score"] / max(top, 1) * 10, 1)
        if iq.get("probabilities"):
            out["probabilities"]["interest"] = iq["probabilities"]
    for key in ("frame", "template"):
        c = ans.get(key, {}) or {}
        if isinstance(c, dict):
            if c.get("choice") in (FRAME_CHOICES if key == "frame" else TEMPLATE_CHOICES):
                out[key] = c["choice"]
            if c.get("probabilities"):
                out["probabilities"][key] = c["probabilities"]
        elif isinstance(c, str):
            out[key] = c
    m = ans.get("monetary", {}) or {}
    if isinstance(m, dict):
        p = m.get("noul", m.get("probability"))
        if isinstance(p, (int, float)):
            out["monetary"] = p > 0.5
            out["probabilities"]["monetary_p"] = p
    elif isinstance(m, bool):
        out["monetary"] = m
    return out


def route_signal(signal_id=None):
    """Jev verdict on one signal: interest, frame, monetary, template.

    Origin is always reported: live Jev when a provider key is configured,
    deterministic fallback otherwise. Jev chooses; code executes.
    """
    if not signal_id:
        return {"status": "error", "reason": "Pass signal_id from signals_top."}
    seed = _resolve_signal(signal_id)
    if not seed:
        return {"status": "error", "reason": f"Unknown signal_id '{signal_id}'."}
    questions = _router_questions(seed)
    if _jev_provider() is None:
        verdict = _deterministic_verdict(seed)
        return {"status": "ok", "signal_id": signal_id, "origin": "deterministic",
                "note": "No JEV provider key (OPENROUTER_API_KEY/TYPESAFE_API_KEY).",
                "verdict": verdict}
    res = _jev_ask(seed, questions)
    if res["status"] != "ok":
        verdict = _deterministic_verdict(seed)
        verdict["provider_error"] = res["reason"]
        return {"status": "ok", "signal_id": signal_id, "origin": "deterministic",
                "note": "Provider failed; fell back.", "verdict": verdict}
    verdict = _parse_jev_answers(res["answers"])
    if verdict["template"] is None or verdict["template"] not in TEMPLATES:
        verdict["template"] = TEMPLATE_FOR_TYPE.get(seed.get("type"), "anomaly")
    if verdict["frame"] is None or verdict["frame"] not in FRAME_CHOICES:
        verdict["frame"] = _deterministic_verdict(seed)["frame"]
    return {"status": "ok", "signal_id": signal_id, "origin": res["origin"],
            "verdict": verdict, "raw": res["answers"]}


def rank_signals(garden="powpowpow", limit=10):
    """Top signals ranked by Jev interest (or deterministic score)."""
    try:
        limit = max(1, min(int(limit), 10))
    except (TypeError, ValueError):
        limit = 10
    res = signals_top(garden, 25)
    if res.get("status") != "ok":
        return res
    ranked = []
    for s in res["signals"]:
        if not s.get("eligible"):
            continue
        r = route_signal(s["id"])
        v = r.get("verdict", {})
        ranked.append({"signal": s, "origin": r.get("origin", "deterministic"),
                       "interest": v.get("interest"),
                       "frame": v.get("frame"), "template": v.get("template")})
        if len(ranked) >= limit:
            break
    ranked.sort(key=lambda e: (e["interest"] is not None, e["interest"] or 0),
                reverse=True)
    origins = {e["origin"] for e in ranked}
    return {"status": "ok", "garden": garden,
            "origin": origins.pop() if len(origins) == 1 else "mixed",
            "ranked": ranked}


def content_status():
    """What can this factory actually do right now (truth contract)."""
    prov = _jev_provider()
    return {
        "status": "ok",
        "jev": {"provider": prov["name"] if prov else None,
                "model": prov["model"] if prov else None,
                "mode": "live" if prov else "deterministic-fallback"},
        "renderers": {
            "hyperframes": bool(shutil.which("npx")),
            "ffmpeg": bool(shutil.which("ffmpeg")),
            "clipforge_zero": (ROOT / "clipforge-zero").exists(),
        },
        "audio": {
            "edge_tts": EDGE_TTS_BIN.exists(),
            "brand_kit": "not built — Stable Audio recipes pending",
        },
        "data": {
            "powpowpow_live_cards": POW_CARDS.exists(),
            "ukgraph_planning": UK_PLANNING.exists(),
            "ukgraph_contracts": UK_CONTRACTS.exists(),
        },
        "publishing": "manual only — Taisly dry-run pending",
        "store": str(STORE),
    }


def lineage(limit=20):
    """signal_id -> video_id attachment log. Latest per content_id only."""
    if not LINEAGE.exists():
        return {"status": "ok", "entries": []}
    rows = [json.loads(l) for l in LINEAGE.read_text().splitlines() if l.strip()]
    try:
        limit = max(1, min(int(limit), 100))
    except (TypeError, ValueError):
        limit = 20
    seen = {}
    for r in rows:
        cid = r.get("content_id", "")
        if cid:
            seen[cid] = r
    deduped = list(seen.values())
    return {"status": "ok", "entries": deduped[-limit:]}


PROOFS_DIR = STORE / "proofs"
PROOFS_DIR.mkdir(parents=True, exist_ok=True)


def _load_proof(proof_id):
    p = PROOFS_DIR / f"{proof_id}.json"
    if not p.exists():
        return None
    return json.loads(p.read_text())


def ingest(signal_id=None):
    """Anything -> ContentSource. Accepts a signal_id, stores a Proof."""
    from core import proof_from_signal, append_receipt
    if not signal_id:
        return {"status": "error", "reason": "Pass signal_id from signals_top."}
    seed = _resolve_signal(signal_id)
    if not seed:
        return {"status": "error", "reason": f"Unknown signal_id '{signal_id}'."}
    try:
        proof = proof_from_signal(seed, seed.get("garden", ""))
    except ValueError as e:
        return {"status": "error", "reason": str(e)}
    (PROOFS_DIR / f"{proof.proof_id}.json").write_text(json.dumps(
        {**proof.to_dict(), "signal_id": seed["id"],
         "garden": seed.get("garden", "")}, indent=2))
    rcpt = append_receipt("ingest", {"proof_id": proof.proof_id,
                                     "signal_id": seed["id"]})
    return {"status": "ok", "proof": proof.to_dict(), "signal_id": seed["id"],
            "garden": seed.get("garden", ""), "receipt_id": rcpt["receipt_id"]}


def compile(proof_id=None, query="OPPORTUNITY"):
    """Proof + channel + objective -> ContentSpec (gated)."""
    from core import append_receipt, run_gates
    if not proof_id:
        return {"status": "error", "reason": "Pass proof_id from ingest."}
    stored = _load_proof(proof_id)
    if not stored:
        return {"status": "error", "reason": f"Unknown proof_id '{proof_id}'."}
    res = content_from_signal(stored["signal_id"], query)
    if res.get("status") != "ok":
        return res
    content = res["content"]
    from core import Proof
    proof = Proof(proof_id=stored["proof_id"], kind=stored["kind"],
                  source=stored["source"], subject=stored["subject"],
                  claims=stored["claims"], evidence_refs=stored["evidence_refs"],
                  observed_at=stored["observed_at"])
    gates = run_gates(proof, stored["signal_id"], content["template"], content)
    rcpt = append_receipt("compile", {"proof_id": proof_id,
                                      "content_id": res["content_id"],
                                      "template": content["template"],
                                      "gates": gates["gates"]},
                          status="ok" if gates["passed"] else "FAIL",
                          detail="" if gates["passed"] else "gates failed")
    return {**res, "gates": gates,
            "compile_receipt_id": rcpt["receipt_id"]}


def render(content_id=None):
    """ContentSpec -> artifact via the dependency graph (gated)."""
    from core import append_receipt, Artifact
    if not content_id:
        return {"status": "error", "reason": "Pass content_id from compile."}
    src = STORE / f"{content_id}.json"
    if not src.exists():
        return {"status": "error", "reason": f"Unknown content_id '{content_id}'."}
    content = json.loads(src.read_text())
    res = render_video(content_id)
    if res.get("status") != "ok":
        append_receipt("render", {"content_id": content_id}, status="FAIL",
                       detail=res.get("reason", "")[:200])
        return res
    art = Artifact(artifact_id=res["video_id"], kind="video", path=res["mp4"],
                   proof_id="", signal_id=res.get("signal_id", ""),
                   processors={"render": "render.hyperframes",
                               "voice": "voice.edge_tts"})
    rcpt = append_receipt("render", {"content_id": content_id,
                                     "video_id": res["video_id"],
                                     "signal_id": res.get("signal_id"),
                                     "template": content.get("template"),
                                     "artifact": art.to_dict()})
    return {**res, "artifact": art.to_dict(), "render_receipt_id": rcpt["receipt_id"]}


def publish(video_id=None, platform="youtube"):
    """Platform adapters. Manual until Taisly is wired — receipt says so."""
    from core import append_receipt
    if not video_id:
        return {"status": "error", "reason": "Pass video_id from render."}
    rcpt = append_receipt("publish", {"video_id": video_id, "platform": platform},
                          status="manual-pending",
                          detail="No uploader wired. Upload manually, then measure().")
    return {"status": "manual-pending", "video_id": video_id,
            "platform": platform,
            "instruction": "Upload the MP4 manually, then call measure().",
            "publish_receipt_id": rcpt["receipt_id"]}


def measure(video_id=None, metrics=None):
    """Performance observation back into the receipt chain."""
    from core import append_receipt
    if not video_id:
        return {"status": "error", "reason": "Pass video_id from render."}
    metrics = metrics or {}
    rcpt = append_receipt("measure", {"video_id": video_id, "metrics": metrics})
    return {"status": "ok", "video_id": video_id,
            "receipt_id": rcpt["receipt_id"]}


def run(signal_id=None, query="OPPORTUNITY"):
    """Convenience: signal -> finished post (ingest/compile/render/narrate)."""
    ing = ingest(signal_id)
    if ing.get("status") != "ok":
        return ing
    comp = compile(ing["proof"]["proof_id"], query)
    if comp.get("status") != "ok":
        return comp
    if not comp.get("gates", {}).get("passed"):
        existing = STORE / f"{comp.get('content_id','')}.json"
        if not existing.exists():
            return {"status": "FAIL", "stage": "compile", "gates": comp["gates"],
                    "compile_receipt_id": comp.get("compile_receipt_id")}
    nar = render_narration(comp["content_id"])
    if nar.get("status") != "ok":
        return {"status": "FAIL", "stage": "narration", **nar}
    mix = STORE / f"{comp['content_id']}.mix.mp3"
    mix_out = _mix_audio(Path(nar["audio"]), mix)
    nar["mix"] = mix_out
    rnd = render(comp["content_id"])
    if rnd.get("status") != "ok":
        return {"status": "FAIL", "stage": "render", **rnd}
    streams = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "stream=codec_type",
         "-of", "csv=p=0", rnd["mp4"]],
        capture_output=True, text=True, timeout=30).stdout.split()
    return {"status": "ok", "signal_id": signal_id, "query": query,
            "proof_id": ing["proof"]["proof_id"],
            "content_id": comp["content_id"], "video_id": rnd["video_id"],
            "mp4": rnd["mp4"], "narration": nar.get("audio"),
            "streams": streams,
            "receipts": {"ingest": ing["receipt_id"],
                         "compile": comp["compile_receipt_id"],
                         "render": rnd["render_receipt_id"]}}


def inspect(target="graph"):
    """Show graph, processors, costs, artifacts, receipts, proofs."""
    from core import verify_chain
    import yaml
    target = (target or "graph").lower()
    if target == "graph":
        procs = yaml.safe_load((ROOT / "registry" / "processors.yaml").read_text())
        mods = yaml.safe_load((ROOT / "registry" / "modules.yaml").read_text())
        tmpls = yaml.safe_load((ROOT / "registry" / "templates.yaml").read_text())
        return {"status": "ok", "processors": procs, "modules": mods,
                "templates": tmpls}
    if target == "receipts":
        return {"status": "ok", **verify_chain()}
    if target == "proofs":
        return {"status": "ok",
                "proofs": [json.loads(p.read_text()) for p in sorted(PROOFS_DIR.glob("*.json"))]}
    if target.startswith("proof:"):
        stored = _load_proof(target.split(":", 1)[1])
        return {"status": "ok", "proof": stored} if stored else {
            "status": "error", "reason": "unknown proof"}
    return {"status": "error",
            "reason": "Use graph | receipts | proofs | proof:<id>."}


TOOLS = [
    {"name": "signals_top",
     "description": "Top deterministic signals for a garden (powpowpow | ukgraph). Evidence-linked, no invented metrics.",
     "inputSchema": {"type": "object",
                     "properties": {"garden": {"type": "string"}, "limit": {"type": "integer"}},
                     "required": ["garden"]}},
    {"name": "list_templates",
     "description": "Template catalogue and signal.type -> template mapping.",
     "inputSchema": {"type": "object", "properties": {}}},
    {"name": "build_content",
     "description": "Signal JSON -> content.json (hook + beats + source label). Deterministic, refuses metric-less signals.",
     "inputSchema": {"type": "object",
                     "properties": {"signal": {"type": "object"},
                                    "template": {"type": "string"}},
                     "required": ["signal"]}},
    {"name": "expand_signal",
     "description": "Seed signal -> supporting graph neighbourhood (2-4 strongest facts, same garden).",
     "inputSchema": {"type": "object",
                     "properties": {"signal_id": {"type": "string"}},
                     "required": ["signal_id"]}},
    {"name": "content_from_signal",
     "description": "Seed signal + query (CHANGE|WHY|WHERE|COMPARE|OPPORTUNITY|WARNING) -> render manifest (hook/claim/proof/close/source_ids). Worthiness-gated.",
     "inputSchema": {"type": "object",
                     "properties": {"signal_id": {"type": "string"},
                                    "query": {"type": "string"}},
                     "required": ["signal_id"]}},
    {"name": "render_video",
     "description": "Render content_id to 9:16 MP4 via HyperFrames. Logs signal_id -> video_id lineage.",
     "inputSchema": {"type": "object",
                     "properties": {"content_id": {"type": "string"}},
                     "required": ["content_id"]}},
    {"name": "render_narration",
     "description": "Content beats -> narration audio via $0 Edge TTS.",
     "inputSchema": {"type": "object",
                     "properties": {"content_id": {"type": "string"},
                                    "voice": {"type": "string"}},
                     "required": ["content_id"]}},
    {"name": "route_signal",
     "description": "Jev verdict on one signal (interest/frame/monetary/template). Reports origin: live Jev or deterministic fallback.",
     "inputSchema": {"type": "object",
                     "properties": {"signal_id": {"type": "string"}},
                     "required": ["signal_id"]}},
    {"name": "rank_signals",
     "description": "Top eligible signals for a garden, ranked by Jev interest (or deterministic score).",
     "inputSchema": {"type": "object",
                     "properties": {"garden": {"type": "string"},
                                    "limit": {"type": "integer"}},
                     "required": ["garden"]}},
    {"name": "content_status",
     "description": "What this factory can actually do right now.",
     "inputSchema": {"type": "object", "properties": {}}},
    {"name": "lineage",
     "description": "signal_id -> video_id attachment log.",
     "inputSchema": {"type": "object",
                     "properties": {"limit": {"type": "integer"}}}},
    {"name": "ingest",
     "description": "Anything -> ContentSource. Signal ID in, stored Proof out. No proof without metrics+evidence.",
     "inputSchema": {"type": "object",
                     "properties": {"signal_id": {"type": "string"}},
                     "required": ["signal_id"]}},
    {"name": "compile",
     "description": "Proof + objective -> ContentSpec. Runs evidence-fresh, no-duplicate, claim-resolved gates.",
     "inputSchema": {"type": "object",
                     "properties": {"proof_id": {"type": "string"},
                                    "query": {"type": "string"}},
                     "required": ["proof_id"]}},
    {"name": "render",
     "description": "ContentSpec -> video artifact via the dependency graph. Gate failures become FAIL receipts.",
     "inputSchema": {"type": "object",
                     "properties": {"content_id": {"type": "string"}},
                     "required": ["content_id"]}},
    {"name": "publish",
     "description": "Platform adapters. Manual until an uploader is wired; receipt says manual-pending.",
     "inputSchema": {"type": "object",
                     "properties": {"video_id": {"type": "string"},
                                    "platform": {"type": "string"}},
                     "required": ["video_id"]}},
    {"name": "measure",
     "description": "Performance observation back into the receipt chain.",
     "inputSchema": {"type": "object",
                     "properties": {"video_id": {"type": "string"},
                                    "metrics": {"type": "object"}},
                     "required": ["video_id"]}},
    {"name": "run",
     "description": "Convenience: signal -> finished post (ingest/compile/render/narrate with receipts).",
     "inputSchema": {"type": "object",
                     "properties": {"signal_id": {"type": "string"},
                                    "query": {"type": "string"}},
                     "required": ["signal_id"]}},
    {"name": "inspect",
     "description": "Show dependency graph, receipts chain, proofs, or one proof (graph|receipts|proofs|proof:<id>).",
     "inputSchema": {"type": "object",
                     "properties": {"target": {"type": "string"}}}},
    {"name": "concepts_top",
     "description": "Concept topics from the powpowpow registry (10 coins + categories) with explainer angles.",
     "inputSchema": {"type": "object", "properties": {}}},
    {"name": "concept_explain",
     "description": "Concept angle (explain|why-now|economics|hardware|signal) -> gated explainer content. Analytical only.",
     "inputSchema": {"type": "object",
                     "properties": {"topic": {"type": "string"},
                                    "angle": {"type": "string"}},
                     "required": ["topic"]}},
    {"name": "relationships",
     "description": "Two topics -> analytical comparison of how approaches differ. Never recommendations.",
     "inputSchema": {"type": "object",
                     "properties": {"a": {"type": "string"}, "b": {"type": "string"}},
                     "required": ["a", "b"]}},
    {"name": "theses_top",
     "description": "Curated evergreen theses (useful-PoW question, privacy-in-AGI, physical bottlenecks).",
     "inputSchema": {"type": "object", "properties": {}}},
]

DISPATCH = {t["name"]: globals()[t["name"]] for t in TOOLS}


def handle_tool_call(name, args):
    func = DISPATCH.get(name)
    if not func:
        return {"error": f"Unknown tool: {name}"}
    try:
        return func(**(args or {}))
    except TypeError as e:
        return {"error": f"Invalid args: {e}"}


def run_mcp_stdio():
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            continue
        method = msg.get("method", "")
        msg_id = msg.get("id")
        if method == "initialize":
            response = {"jsonrpc": "2.0", "id": msg_id,
                        "result": {"protocolVersion": "2024-11-05",
                                   "capabilities": {"tools": {}},
                                   "serverInfo": {"name": "content-sensor",
                                                  "version": "0.1.0",
                                                  "description": ("V1 content factory: signals -> "
                                                                  "content.json -> HyperFrames MP4. "
                                                                  "Evidence-linked, manual publish.")}}}
        elif method == "tools/list":
            response = {"jsonrpc": "2.0", "id": msg_id, "result": {"tools": TOOLS}}
        elif method == "tools/call":
            params = msg.get("params", {})
            result = handle_tool_call(params.get("name", ""), params.get("arguments", {}))
            response = {"jsonrpc": "2.0", "id": msg_id,
                        "result": {"content": [{"type": "text",
                                                "text": json.dumps(result, indent=2, default=str)}]}}
        else:
            response = {"jsonrpc": "2.0", "id": msg_id,
                        "error": {"code": -32601, "message": f"Method not found: {method}"}}
        print(json.dumps(response), flush=True)


if __name__ == "__main__":
    if "--serve" in sys.argv:
        run_mcp_stdio()
    elif len(sys.argv) > 2:
        print(json.dumps(handle_tool_call(sys.argv[1], json.loads(sys.argv[2])),
                         indent=2, default=str))
    else:
        print(json.dumps({"name": "content-sensor", "version": "0.1.0",
                          "tools": [t["name"] for t in TOOLS]}, indent=2))
