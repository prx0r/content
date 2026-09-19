"""Kernel tests: propose-only processors, proof refusal, gates, chain."""
import json
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.processor import ProcessorSpec, Proposal, run_processor
from core.proof import proof_from_signal
from core.gates import gate_claim_resolved, gate_no_duplicate
from core import receipt as receipt_mod


def test_forbidden_keys_become_failure():
    spec = ProcessorSpec("evil.render", 1, {"x": "str"})
    p = run_processor(spec, {"x": "y"}, lambda i: {"receipt": "minted!", "out": 1})
    assert p.failure and "forbidden" in p.failure
    assert p.outputs == {}


def test_input_outside_schema_rejected():
    spec = ProcessorSpec("picky", 1, {"x": "str"})
    with pytest.raises(ValueError):
        run_processor(spec, {"y": 1}, lambda i: {})


def test_no_proof_without_metrics():
    with pytest.raises(ValueError):
        proof_from_signal({"id": "sig_x", "metrics": [], "evidence": [1]})


def test_no_proof_without_evidence():
    with pytest.raises(ValueError):
        proof_from_signal({"id": "sig_x", "metrics": [{"name": "m"}],
                           "evidence": []})


def test_proof_is_deterministic():
    sig = {"id": "sig_1", "entities": ["PRL"], "claim": "c",
           "metrics": [{"name": "m", "value": 1, "unit": "u"}],
           "evidence": [{"file": "f"}], "updated_at": "t"}
    assert (proof_from_signal(sig).proof_id
            == proof_from_signal(sig).proof_id)


def test_gate_rejects_untraced_beat():
    content = {"beats": ["The moon is made of cheese"],
               "metrics": [{"name": "price_usd"}],
               "source_ids": ["sig_1"]}
    ok, detail = gate_claim_resolved(content)
    assert not ok


def test_gate_accepts_supporting_claim():
    content = {"beats": ["Submit before the deadline."],
               "metrics": [{"name": "price_usd"}],
               "supporting_claims": ["Submit before the deadline."],
               "source_ids": ["sig_1", "sig_2"]}
    ok, _ = gate_claim_resolved(content)
    assert ok


def test_receipt_chain(tmp_path, monkeypatch):
    f = tmp_path / "chain.jsonl"
    monkeypatch.setattr(receipt_mod, "RECEIPTS_FILE", f)
    r1 = receipt_mod.append_receipt("ingest", {"a": 1})
    r2 = receipt_mod.append_receipt("render", {"b": 2})
    assert r2["prev"] == r1["receipt_id"]
    v = receipt_mod.verify_chain()
    assert v["status"] == "ok" and v["receipts"] == 2
    # tamper -> FAIL
    lines = f.read_text().splitlines()
    row = json.loads(lines[1])
    row["ref"] = {"b": 999}
    lines[1] = json.dumps(row)
    f.write_text("\n".join(lines) + "\n")
    assert receipt_mod.verify_chain()["status"] == "FAIL"
