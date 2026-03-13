"""Adaptive attack strategies for ATLAS red-teaming.

This package provides automated, LLM-driven attack strategies that
iteratively refine adversarial prompts based on a target model's
responses. Each strategy uses a separate "attacker" LLM to generate,
evaluate, and improve adversarial inputs.

Available strategies:

- **TAPStrategy** -- Tree of Attacks with Pruning.  Explores a tree of
  attack variations, prunes low-scoring branches, and expands promising
  ones.  Best for broad coverage.

- **PAIRStrategy** -- Prompt Automatic Iterative Refinement.  Runs a
  tight iterative loop where each new prompt is informed by the
  target's previous refusal.  Best for depth-first refinement.

These modules are intended for authorized security research and testing only.
"""

from atlas.probes.strategies.pair import PAIRStrategy
from atlas.probes.strategies.tap import TAPStrategy

__all__ = [
    "PAIRStrategy",
    "TAPStrategy",
]
