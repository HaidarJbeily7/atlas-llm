"""Judge robustness checker.

Runs the same findings through each judge multiple times to measure
verdict consistency. A robust judge should produce the same verdict
>90% of the time for the same input.
"""
from __future__ import annotations

import asyncio
import random
from typing import Any

from pydantic import BaseModel, Field

from atlas.core.models import Finding
from atlas.detectors.base import BaseDetector
from atlas.logging.setup import get_logger

logger = get_logger(__name__)


class JudgeConsistencyResult(BaseModel):
    """Consistency result for a single judge."""

    judge_name: str
    total_checks: int = 0
    consistent_checks: int = 0
    consistency_rate: float = 0.0
    is_robust: bool = True  # True if >= 90%
    per_finding: list[dict[str, Any]] = Field(default_factory=list)


class RobustnessReport(BaseModel):
    """Overall robustness report across all judges."""

    judges: list[JudgeConsistencyResult] = Field(default_factory=list)
    overall_consistency: float = 0.0
    all_robust: bool = True
    sample_size: int = 0
    repetitions: int = 0


async def check_judge_robustness(
    findings: list[Finding],
    detectors: list[BaseDetector],
    sample_size: int = 10,
    repetitions: int = 3,
    judge_names: set[str] | None = None,
) -> RobustnessReport:
    """Run robustness checks on LLM-based judges.

    Args:
        findings: Pool of findings to sample from.
        detectors: All available detectors (filters to judges only).
        sample_size: Number of findings to test.
        repetitions: Number of times to run each judge per finding.
        judge_names: Which detectors to test. Defaults to LLM judges.
    """
    if judge_names is None:
        judge_names = {"llm_judge", "semantic_judge", "safety_judge"}

    judges = [d for d in detectors if d.name in judge_names]
    if not judges:
        logger.warning("judge_robustness_no_judges_found")
        return RobustnessReport()

    # Sample findings
    pool = [f for f in findings if f.attempt.response]
    if len(pool) > sample_size:
        sample = random.sample(pool, sample_size)
    else:
        sample = pool

    if not sample:
        logger.warning("judge_robustness_no_findings")
        return RobustnessReport(sample_size=0, repetitions=repetitions)

    results: list[JudgeConsistencyResult] = []

    for judge in judges:
        total_checks = 0
        consistent_checks = 0
        per_finding: list[dict[str, Any]] = []

        for finding in sample:
            verdicts: list[bool] = []

            for _ in range(repetitions):
                try:
                    result = await judge.detect(finding.attempt)
                    verdicts.append(result.passed)
                except Exception as exc:
                    logger.warning(
                        "judge_robustness_error",
                        judge=judge.name,
                        error=str(exc),
                    )
                    continue

            if len(verdicts) >= 2:
                total_checks += 1
                is_consistent = len(set(verdicts)) == 1
                if is_consistent:
                    consistent_checks += 1

                per_finding.append({
                    "finding_id": finding.id,
                    "verdicts": verdicts,
                    "consistent": is_consistent,
                })

        consistency_rate = (
            consistent_checks / total_checks if total_checks else 0.0
        )
        is_robust = consistency_rate >= 0.9

        if not is_robust:
            logger.warning(
                "judge_not_robust",
                judge=judge.name,
                consistency_rate=f"{consistency_rate:.1%}",
                threshold="90%",
            )

        results.append(JudgeConsistencyResult(
            judge_name=judge.name,
            total_checks=total_checks,
            consistent_checks=consistent_checks,
            consistency_rate=round(consistency_rate, 4),
            is_robust=is_robust,
            per_finding=per_finding,
        ))

    overall = (
        sum(r.consistency_rate for r in results) / len(results)
        if results else 0.0
    )

    return RobustnessReport(
        judges=results,
        overall_consistency=round(overall, 4),
        all_robust=all(r.is_robust for r in results),
        sample_size=len(sample),
        repetitions=repetitions,
    )
