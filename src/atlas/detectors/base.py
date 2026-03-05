"""Base detector and composable combinators for ATLAS."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from atlas.core.models import Attempt, DetectorResult


class BaseDetector(ABC):
    """Abstract base for all detectors."""

    name: str = ""
    description: str = ""

    @abstractmethod
    async def detect(self, attempt: Attempt) -> DetectorResult:
        """Analyze an attempt and return detection result.

        Args:
            attempt: The attempt to analyze (must have response filled in).

        Returns:
            DetectorResult with passed=True if the response is safe.
        """
        ...


class CompositeDetector(BaseDetector):
    """Base for composite detectors that combine multiple detectors."""

    def __init__(self, *detectors: BaseDetector) -> None:
        self.detectors = detectors


class AnyOfDetector(CompositeDetector):
    """Fails if ANY detector flags the response (OR logic).

    Use when you want to catch responses flagged by any single detector.
    """
    name = "any_of"

    async def detect(self, attempt: Attempt) -> DetectorResult:
        results = []
        for detector in self.detectors:
            result = await detector.detect(attempt)
            results.append(result)

        # Passes only if ALL detectors pass
        all_passed = all(r.passed for r in results)
        # Use worst (lowest for passed, highest for failed) score
        scores = [r.score for r in results]
        worst_score = min(scores) if scores else 0.0
        avg_confidence = sum(r.confidence for r in results) / len(results) if results else 1.0

        failed_names = [r.detector_name for r in results if not r.passed]
        evidence = f"Flagged by: {', '.join(failed_names)}" if failed_names else "All detectors passed"

        return DetectorResult(
            detector_name=self.name,
            passed=all_passed,
            score=worst_score,
            confidence=avg_confidence,
            evidence=evidence,
        )


class AllOfDetector(CompositeDetector):
    """Fails only if ALL detectors flag the response (AND logic).

    Use for high-confidence detection requiring agreement.
    """
    name = "all_of"

    async def detect(self, attempt: Attempt) -> DetectorResult:
        results = []
        for detector in self.detectors:
            result = await detector.detect(attempt)
            results.append(result)

        # Fails only if ALL detectors fail
        all_failed = all(not r.passed for r in results)
        passed = not all_failed
        avg_score = sum(r.score for r in results) / len(results) if results else 0.0
        avg_confidence = sum(r.confidence for r in results) / len(results) if results else 1.0

        failed_count = sum(1 for r in results if not r.passed)
        evidence = f"{failed_count}/{len(results)} detectors flagged"

        return DetectorResult(
            detector_name=self.name,
            passed=passed,
            score=avg_score,
            confidence=avg_confidence,
            evidence=evidence,
        )


class NoneOfDetector(CompositeDetector):
    """Passes only if NONE of the detectors flag the response.

    Equivalent to AnyOfDetector but with inverted semantics for clarity.
    """
    name = "none_of"

    async def detect(self, attempt: Attempt) -> DetectorResult:
        results = []
        for detector in self.detectors:
            result = await detector.detect(attempt)
            results.append(result)

        # Passes only if ALL detectors pass (none flag)
        none_flagged = all(r.passed for r in results)
        best_score = max((r.score for r in results), default=1.0)
        avg_confidence = sum(r.confidence for r in results) / len(results) if results else 1.0

        flagged = [r.detector_name for r in results if not r.passed]
        evidence = f"Flagged by: {', '.join(flagged)}" if flagged else "No detectors flagged"

        return DetectorResult(
            detector_name=self.name,
            passed=none_flagged,
            score=best_score,
            confidence=avg_confidence,
            evidence=evidence,
        )


# Convenience factory functions
def any_of(*detectors: BaseDetector) -> AnyOfDetector:
    """Create a detector that fails if ANY sub-detector flags."""
    return AnyOfDetector(*detectors)

def all_of(*detectors: BaseDetector) -> AllOfDetector:
    """Create a detector that fails only if ALL sub-detectors flag."""
    return AllOfDetector(*detectors)

def none_of(*detectors: BaseDetector) -> NoneOfDetector:
    """Create a detector that passes only if NONE flag."""
    return NoneOfDetector(*detectors)
