"""Simple pass/fail threshold evaluator."""
from __future__ import annotations

from typing import Any

from atlas.core.models import Finding
from atlas.evaluators.base import BaseEvaluator
from atlas.plugins.registry import register


@register("evaluators", name="threshold")
class ThresholdEvaluator(BaseEvaluator):
    """Pass/fail based on pass rate threshold."""

    name = "threshold"

    def __init__(self, pass_rate_threshold: float = 80.0) -> None:
        self.pass_rate_threshold = pass_rate_threshold

    def evaluate(self, findings: list[Finding]) -> dict[str, Any]:
        if not findings:
            return {"passed": True, "pass_rate": 100.0, "threshold": self.pass_rate_threshold}

        total = len(findings)
        passed = sum(1 for f in findings if f.passed)
        pass_rate = (passed / total) * 100

        return {
            "passed": pass_rate >= self.pass_rate_threshold,
            "pass_rate": round(pass_rate, 2),
            "threshold": self.pass_rate_threshold,
            "total": total,
            "passed_count": passed,
            "failed_count": total - passed,
        }
