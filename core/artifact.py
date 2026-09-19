"""Artifact — a content output with its full proof chain attached."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Artifact:
    artifact_id: str
    kind: str              # video | audio | spec | script | chart
    path: str
    proof_id: str
    signal_id: str
    processors: dict = field(default_factory=dict)  # step -> processor name
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {"artifact_id": self.artifact_id, "kind": self.kind,
                "path": self.path, "proof_id": self.proof_id,
                "signal_id": self.signal_id, "processors": self.processors,
                "metadata": self.metadata}

    def traverse(self) -> list[str]:
        """video -> spec -> claim -> signal -> proof. Auditable chain."""
        return [self.artifact_id, f"spec:{self.artifact_id}",
                f"signal:{self.signal_id}", f"proof:{self.proof_id}"]
