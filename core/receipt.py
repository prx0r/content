"""Receipts — hash-chained append-only JSONL (ported from influence).

Promotion is a receipt or it didn't happen. FAIL is first-class.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

RECEIPTS_FILE = Path(__file__).parent.parent / "receipts" / "content.jsonl"


def _chain_head() -> str:
    RECEIPTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not RECEIPTS_FILE.exists():
        return "GENESIS"
    last = ""
    with open(RECEIPTS_FILE) as f:
        for line in f:
            if line.strip():
                last = line
    if not last:
        return "GENESIS"
    return json.loads(last).get("receipt_id", "GENESIS")


def append_receipt(kind: str, ref: dict[str, Any],
                   status: str = "ok", detail: str = "") -> dict[str, Any]:
    prev = _chain_head()
    body = {"prev": prev, "kind": kind, "status": status,
            "ref": ref, "detail": detail,
            "at": datetime.now(timezone.utc).isoformat()}
    rid = "rcpt_" + hashlib.sha256(
        json.dumps(body, sort_keys=True).encode()).hexdigest()[:12]
    body["receipt_id"] = rid
    with open(RECEIPTS_FILE, "a") as f:
        f.write(json.dumps(body) + "\n")
    return body


def verify_chain() -> dict[str, Any]:
    if not RECEIPTS_FILE.exists():
        return {"status": "ok", "receipts": 0, "chain": "empty"}
    prev = "GENESIS"
    n = 0
    fails = 0
    with open(RECEIPTS_FILE) as f:
        for line in f:
            if not line.strip():
                continue
            r = json.loads(line)
            if r.get("prev") != prev:
                return {"status": "FAIL", "at": n,
                        "reason": "chain link broken"}
            rid = r.pop("receipt_id")
            calc = "rcpt_" + hashlib.sha256(
                json.dumps(r, sort_keys=True).encode()).hexdigest()[:12]
            if calc != rid:
                return {"status": "FAIL", "at": n,
                        "reason": "receipt hash mismatch"}
            prev = rid
            n += 1
            if r.get("status") == "FAIL":
                fails += 1
    return {"status": "ok", "receipts": n, "fails": fails, "head": prev}
