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
}

CONTENT_WORTHY_TYPES = ("anomaly", "ranking", "geo_signal", "change", "comparison", "causal")


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
    else:
        return {"status": "error",
                "reason": f"Unknown garden '{garden}'. Use 'powpowpow' or 'ukgraph'."}
    if res.get("status") == "ok":
        for s in res["signals"]:
            s["score"], s["eligible"] = _score_signal(s)
        res["signals"].sort(key=lambda s: s.get("score", 0), reverse=True)
    return res


def _all_signals():
    out = []
    for garden in ("powpowpow", "ukgraph"):
        r = signals_top(garden, 25)
        if r.get("status") == "ok":
            for s in r["signals"]:
                s = dict(s)
                s["garden"] = garden
                out.append(s)
    return out


def expand_signal(signal_id=None):
    """Seed signal -> supporting graph neighbourhood (2-4 strongest facts)."""
    if not signal_id:
        return {"status": "error", "reason": "Pass signal_id from signals_top."}
    alls = _all_signals()
    seed = next((s for s in alls if s["id"] == signal_id), None)
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
}

TEMPLATES = {
    "anomaly": {"beats": 3, "use": "one surprising measurement + evidence"},
    "ranking": {"beats": 3, "use": "ordered list, winner first"},
    "vs": {"beats": 3, "use": "A vs B comparison"},
    "what_changed": {"beats": 3, "use": "before/after change"},
    "map": {"beats": 3, "use": "place-anchored precursor signal"},
    "why": {"beats": 3, "use": "causal chain in plain words"},
    "opportunity": {"beats": 4, "use": "what someone can do because of this"},
}

QUERIES = {
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
    for s in supporting[:3]:
        if s.get("claim"):
            proof.append(s["claim"])
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

def _fill_anomaly_html(content):
    sig_title = content.get("hook", "")
    metrics = content.get("metrics", []) or [{}]
    m0 = metrics[0]
    big = m0.get("value", "?")
    try:
        big = f"{float(big):+.0f}{m0.get('unit', '')}"
    except (TypeError, ValueError):
        big = f"{big} {m0.get('unit', '')}".strip()
    beats = content.get("beats", [])
    evidence = (beats[1] if len(beats) > 1 else "") + (
        f" · {content.get('source_label', '')}" if content.get("source_label") else "")
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
        background: #050505; color: #f7f7f5; }}
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
         data-duration="8" data-width="1080" data-height="1920">
      <div class="kicker" id="kicker">{sig_title}</div>
      <div id="metric">{big}</div>
      <div id="label">{m0.get('name', '').replace('_', ' ')}</div>
      <div id="evidence">{evidence}</div>
    </div>
    <script>
      var tl = gsap.timeline({{ paused: true }});
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


def render_video(content_id=None):
    """Render a built content.json to vertical MP4 via HyperFrames."""
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
    (proj / "index.html").write_text(_fill_anomaly_html(content))

    chk = subprocess.run(["npx", "--yes", "hyperframes@0.8.50", "check"],
                         cwd=proj, capture_output=True, text=True, timeout=180)
    if chk.returncode != 0:
        return {"status": "error", "reason": "hyperframes check failed",
                "detail": (chk.stdout + chk.stderr)[-2000:]}

    rnd = subprocess.run(["npx", "--yes", "hyperframes@0.8.50", "render"],
                         cwd=proj, capture_output=True, text=True, timeout=600)
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
    r = subprocess.run([str(EDGE_TTS_BIN), "--voice", voice, "--text", text,
                        "--write-media", str(out)],
                       capture_output=True, text=True, timeout=180)
    if r.returncode != 0 or not out.exists():
        return {"status": "error", "reason": "edge-tts failed",
                "detail": (r.stdout + r.stderr)[-1000:]}
    return {"status": "ok", "content_id": content_id, "audio": str(out),
            "bytes": out.stat().st_size}


# ============================================================
# STATUS + LINEAGE
# ============================================================

def content_status():
    """What can this factory actually do right now (truth contract)."""
    return {
        "status": "ok",
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
    """signal_id -> video_id attachment log."""
    if not LINEAGE.exists():
        return {"status": "ok", "entries": []}
    rows = [json.loads(l) for l in LINEAGE.read_text().splitlines() if l.strip()]
    try:
        limit = max(1, min(int(limit), 100))
    except (TypeError, ValueError):
        limit = 20
    return {"status": "ok", "entries": rows[-limit:]}


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
    {"name": "content_status",
     "description": "What this factory can actually do right now.",
     "inputSchema": {"type": "object", "properties": {}}},
    {"name": "lineage",
     "description": "signal_id -> video_id attachment log.",
     "inputSchema": {"type": "object",
                     "properties": {"limit": {"type": "integer"}}}},
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
