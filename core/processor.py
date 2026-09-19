"""Processors: bounded speculative computation (ported from influence).

A processor takes typed inputs plus a budget and returns proposed outputs,
candidate evidence, and a run record — never truth, never effects.
A processor that writes state, spends, sends, or mints authority is a
protocol violation, caught by tests.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass(frozen=True)
class ProcessorSpec:
    name: str
    version: int
    input_schema: dict[str, Any]
    budget: dict[str, Any] = field(default_factory=dict)
    provides: tuple = ()


@dataclass
class Proposal:
    spec: str
    version: int
    outputs: dict[str, Any]
    evidence: list[dict[str, Any]]
    run: dict[str, Any]
    failure: str | None = None


_FORBIDDEN_KEYS = {"state_after", "grant", "signature", "receipt",
                   "send", "spend", "mint", "publish", "post"}


def run_processor(spec: ProcessorSpec, inputs: dict[str, Any],
                  fn: Callable[[dict], dict]) -> Proposal:
    for key in inputs:
        if key not in spec.input_schema:
            raise ValueError(f"input {key} outside schema")
    out = fn(dict(inputs))
    if not isinstance(out, dict):
        raise ValueError("processor must return a dict")
    bad = _FORBIDDEN_KEYS & set(out)
    if bad:
        return Proposal(spec.name, spec.version, {}, [],
                        {"worker": spec.name},
                        failure=f"forbidden keys: {sorted(bad)}")
    return Proposal(spec.name, spec.version,
                    outputs={k: v for k, v in out.items() if k != "evidence"},
                    evidence=list(out.get("evidence", [])),
                    run={"worker": spec.name, "version": spec.version,
                         "budget": spec.budget})


# --- first-class content processors (adapters live in processors/) ---

def _stub_rank(inputs: dict) -> dict:
    return {"ranked_signal": inputs.get("signal"),
            "evidence": [{"kind": "passthrough"}]}


def _stub_script(inputs: dict) -> dict:
    sig = inputs.get("ranked_signal", {})
    return {"script": {"hook": sig.get("title", ""),
                       "beats": [sig.get("claim", "")]},
            "evidence": [{"kind": "signal", "id": sig.get("id")}]}


PROCESSORS = {
    "jev.rank": ProcessorSpec("jev.rank", 1, {"signal": "dict"},
                              provides=("judge.rank", "judge.score", "judge.choice")),
    "script.short": ProcessorSpec("script.short", 1, {"ranked_signal": "dict"},
                                  provides=("script",)),
    "voice.tts": ProcessorSpec("voice.tts", 1, {"script": "dict"},
                               provides=("voice.tts",)),
    "chart.svg": ProcessorSpec("chart.svg", 1, {"proof": "dict"},
                               provides=("visual.chart",)),
    "render.vertical": ProcessorSpec("render.vertical", 1,
                                     {"content_spec": "dict", "assets": "dict"},
                                     provides=("render.vertical",)),
    "publish.youtube": ProcessorSpec("publish.youtube", 1,
                                     {"artifact": "dict", "metadata": "dict"},
                                     provides=("publish.youtube",)),
}
PROCESSOR_FNS = {"jev.rank": _stub_rank, "script.short": _stub_script}
