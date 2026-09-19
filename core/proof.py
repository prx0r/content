"""Proof — immutable source evidence. No video exists without a proof chain."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass(frozen=True)
class Proof:
    proof_id: str
    kind: str            # graph_signal | observation | measurement
    source: str          # ukgraph | powpowpow | breadup | ukboring
    subject: str
    claims: list = field(default_factory=list)
    evidence_refs: list = field(default_factory=list)
    observed_at: str = ""

    def to_dict(self) -> dict:
        return {"proof_id": self.proof_id, "kind": self.kind,
                "source": self.source, "subject": self.subject,
                "claims": self.claims, "evidence_refs": self.evidence_refs,
                "observed_at": self.observed_at}


def proof_from_signal(signal: dict[str, Any], garden: str = "") -> Proof:
    """A graph signal becomes a Proof. Metric-less signals are refused."""
    if not signal.get("metrics"):
        raise ValueError("signal has no metrics — refusing proof")
    if not signal.get("evidence"):
        raise ValueError("signal has no evidence — refusing proof")
    claims = [signal.get("claim", "")]
    for m in signal.get("metrics", [])[:4]:
        claims.append(f"{m.get('name')}: {m.get('value')} {m.get('unit', '')}".strip())
    pid = "proof_" + hashlib.sha1(json.dumps(
        {"id": signal.get("id"), "claims": claims},
        sort_keys=True).encode()).hexdigest()[:12]
    return Proof(
        proof_id=pid,
        kind="graph_signal",
        source=garden or str(signal.get("garden", "")),
        subject=",".join(signal.get("entities", [])[:3]),
        claims=[c for c in claims if c],
        evidence_refs=list(signal.get("evidence", [])),
        observed_at=signal.get("updated_at") or datetime.now(timezone.utc).isoformat(),
    )
