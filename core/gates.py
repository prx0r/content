"""Content gates (ported from influence base gates).

evidence-fresh-v1 — proof evidence is present and timestamped
no-duplicate-v1   — same signal+template has no ok receipt already
claim-resolved-v1 — every claim traces to a metric or evidence ref
"""
from __future__ import annotations

import json
from typing import Any

from .receipt import RECEIPTS_FILE


def _prior_ok_receipts(kind: str = "") -> list[dict[str, Any]]:
    out = []
    if not RECEIPTS_FILE.exists():
        return out
    with open(RECEIPTS_FILE) as f:
        for line in f:
            if not line.strip():
                continue
            r = json.loads(line)
            if r.get("status") == "ok" and (not kind or r.get("kind") == kind):
                out.append(r)
    return out


def gate_evidence_fresh(proof) -> tuple[bool, str]:
    if not proof.evidence_refs:
        return False, "no evidence refs"
    if not proof.observed_at:
        return False, "no observed_at"
    return True, "evidence present"


def gate_no_duplicate(signal_id: str, template: str) -> tuple[bool, str]:
    for r in _prior_ok_receipts("render"):
        ref = r.get("ref", {})
        if ref.get("signal_id") == signal_id and ref.get("template") == template:
            return False, f"already rendered as {ref.get('video_id')}"
    return True, "novel"


def gate_claim_resolved(content: dict[str, Any]) -> tuple[bool, str]:
    metrics = {m.get("name") for m in content.get("metrics", []) or []}
    values = {str(m.get("value")) for m in content.get("metrics", []) or []
              if m.get("value") is not None}
    claim = str(content.get("claim", ""))
    close = str(content.get("close", ""))
    supporting = [str(c) for c in content.get("supporting_claims", []) or []]
    verbatim_ok = {c for c in [claim, close] if c}
    for i, beat in enumerate(content.get("beats", []) or []):
        b = str(beat)
        bl = b.lower()
        if b and b in verbatim_ok:
            continue  # seed claim/close verbatim — traces to the signal by construction
        if any(k in bl for k in ("http", "evidence", ".json", "ref:")):
            continue
        markers = [m.lower() for m in metrics if m] + [
            "%", "£", "$", "vs", "up", "down", "no ", "best"]
        if any(k in bl for k in markers):
            continue
        if any(v and v in b for v in values):
            continue  # metric value appears verbatim in the beat
        if any(b == s or b in s or s in b for s in supporting if s):
            continue  # traces to a supporting signal's claim (see source_ids)
        return False, f"beat {i} traces to nothing: {beat[:60]}"
    if not content.get("source_ids"):
        return False, "no source_ids"
    return True, "claims resolve"


def run_gates(proof, signal_id: str, template: str,
              content: dict[str, Any]) -> dict[str, Any]:
    results = {
        "evidence-fresh-v1": gate_evidence_fresh(proof),
        "no-duplicate-v1": gate_no_duplicate(signal_id, template),
        "claim-resolved-v1": gate_claim_resolved(content),
    }
    passed = all(ok for ok, _ in results.values())
    return {"passed": passed,
            "gates": {k: {"ok": ok, "detail": d} for k, (ok, d) in results.items()}}
