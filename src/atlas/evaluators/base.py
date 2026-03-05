"""Base evaluator protocol."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from atlas.core.models import Finding


class BaseEvaluator(ABC):
    """Abstract base for evaluators that score/aggregate findings."""

    name: str = ""

    @abstractmethod
    def evaluate(self, findings: list[Finding]) -> dict[str, Any]:
        """Evaluate a list of findings and return scoring results."""
        ...
