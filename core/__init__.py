"""content core — influence kernel ported to media.

Owns intent + graph + contracts + receipts. Never owns TTS, renderers,
uploaders, or models — those are registry dependencies.
"""
from .proof import Proof, proof_from_signal
from .processor import ProcessorSpec, Proposal, run_processor, PROCESSORS, PROCESSOR_FNS
from .artifact import Artifact
from .receipt import append_receipt, verify_chain, RECEIPTS_FILE
from .gates import run_gates

__all__ = ["Proof", "proof_from_signal", "ProcessorSpec", "Proposal",
           "run_processor", "PROCESSORS", "PROCESSOR_FNS", "Artifact",
           "append_receipt", "verify_chain", "RECEIPTS_FILE", "run_gates"]
