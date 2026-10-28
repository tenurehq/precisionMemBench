"""HingeZero original-runtime integration.

The complete original HingeZero_Core.py is copied unchanged from
HingeZero/HingeZero-1B-Memory. This module calls that implementation;
it does not reimplement its nonlinearity, Witness or retaining loop.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from HingeZero_Core import (
    HZ_ALPHA, HZ_EPS, HZ_LAMBDA, HZ_STEPS, HZ_TOP,
    HingeZeroState, HingeZeroWitness, HingeZeroRetainingLoop,
    hinge_phi, hz_recall,
)


def unit(x: np.ndarray) -> np.ndarray:
    v = np.asarray(x, dtype=np.float32)
    n = float(np.linalg.norm(v))
    return v / n if n > 1e-12 else np.zeros_like(v)


def get_witness(bank: np.ndarray, evidence: np.ndarray | None = None) -> HingeZeroWitness:
    matrix = np.asarray(bank, dtype=np.float32)
    if matrix.ndim != 2 or not len(matrix):
        raise ValueError("Witness requires a nonempty bank")
    if evidence is None:
        evidence = np.zeros(len(matrix), dtype=np.float32)
    return HingeZeroWitness(matrix, np.asarray(evidence, dtype=np.float32))


def verify_stored(witness: HingeZeroWitness, index: int) -> HingeZeroState:
    """Tag, observe and witness-verify an exact *stored* memory state."""
    idx = int(index)
    if idx < 0 or idx >= len(witness.memories):
        raise IndexError("Index outside the witnessed memory bank")
    tagged = HingeZeroState(idx, witness.memories[idx])
    if not witness.verify(tagged):
        raise RuntimeError("HingeZero Witness rejected stored-state identity")
    return tagged


def witnessed_recall(
    memory_bank: np.ndarray, query: np.ndarray, *,
    candidate_evidence: np.ndarray | None = None
) -> tuple[HingeZeroWitness, np.ndarray, np.ndarray, HingeZeroState]:
    """Call the original eight-step HingeZero Witness and its hypothesis order."""
    memories = np.asarray(memory_bank, np.float32)
    q = unit(query)
    if candidate_evidence is None:
        candidate_evidence = memories @ q
    witness = get_witness(memories, candidate_evidence)
    stabilized = witness.refine(q)
    scores = witness.memories @ stabilized
    order, locked = witness.hypotheses(q, scores)
    if not witness.verify(locked):
        raise RuntimeError("Witness failed to verify locked recalled state")
    return witness, np.asarray(order, dtype=np.int64), scores, locked


def retaining_checkpoint(witness: HingeZeroWitness, checkpoint_index: int,
                         cue: np.ndarray | None = None,
                         commit_margin: float = 0.10) -> tuple[HingeZeroState, dict]:
    """Actually execute the original retaining loop, not a substitute."""
    initial = verify_stored(witness, checkpoint_index)
    loop = HingeZeroRetainingLoop(
        witness, initial, drift_boundary=0.15, commit_margin=commit_margin)
    if cue is None:
        # No new semantic evidence: test stable holding and witness integrity.
        result = loop.step(disturbance=np.zeros_like(initial.state))
    else:
        result = loop.step(cue=unit(cue))
    state = result["state"]
    if not witness.verify(state):
        raise RuntimeError("HingeZero retaining checkpoint failed Witness verification")
    return state, result


def refine(query: np.ndarray, candidates: np.ndarray, *, steps: int = HZ_STEPS,
           alpha: float = HZ_ALPHA, eps: float = HZ_EPS,
           lam: float = HZ_LAMBDA) -> np.ndarray:
    """Compatibility entrypoint: original full Witness when canonical settings used.

    Custom settings are intentionally rejected rather than silently swapping in
    a different approximation. Use HingeZero_Core.hz_recall for matrix dynamics.
    """
    if (steps, alpha, eps, lam) != (HZ_STEPS, HZ_ALPHA, HZ_EPS, HZ_LAMBDA):
        raise ValueError("The full HingeZero Witness uses original canonical parameters")
    q = unit(query)
    bank = np.asarray(candidates, np.float32)
    if not len(bank):
        return q
    witness = get_witness(bank, bank @ q)
    return witness.refine(q)
