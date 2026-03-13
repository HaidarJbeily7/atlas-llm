"""Comparative benchmarking engine for ATLAS.

Runs identical probe attempts against multiple LLM models concurrently
and produces a ComparisonResult with a ranked leaderboard.

Usage:
    from atlas.engine.comparator import ModelComparator
    from atlas.config.models import AtlasConfig

    comparator = ModelComparator(base_config)
    result = await comparator.compare(
        models=["openai/gpt-4o", "anthropic/claude-3-5-sonnet"],
        probe_names=["agent_harm"],
    )
    for entry in result.leaderboard:
        print(f"{entry.model_name}: {entry.overall_score:.1f}")
"""

from __future__ import annotations

import asyncio
import time
import uuid
from copy import deepcopy
from datetime import UTC, datetime
from typing import Any

from atlas.config.models import AtlasConfig, ProviderConfig
from atlas.core.models import ComparisonResult, ModelScore, ScanResult
from atlas.engine.runner import ScanRunner
from atlas.logging.setup import get_logger

logger = get_logger(__name__)


class ModelComparator:
    """Comparative benchmarking engine that evaluates multiple models.

    Given a base configuration, the comparator creates per-model configs
    by swapping the provider model string, then runs all scans concurrently
    using ``asyncio.gather``.  The results are aggregated into a
    :class:`ComparisonResult` with a leaderboard sorted by overall score
    (descending).
    """

    def __init__(self, base_config: AtlasConfig) -> None:
        self.base_config = base_config

    async def compare(
        self,
        models: list[str],
        profile: str | None = None,
        probe_names: list[str] | None = None,
        detector_names: list[str] | None = None,
    ) -> ComparisonResult:
        """Run identical scans against *models* and return a comparison.

        Args:
            models: List of LiteLLM model strings to evaluate.
            profile: Scan profile name (e.g. "quick", "standard").
            probe_names: Explicit list of probe names to run.
            detector_names: Explicit list of detector names to use.

        Returns:
            A :class:`ComparisonResult` containing per-model scan results
            and a ranked leaderboard.
        """
        if not models:
            raise ValueError("At least one model must be provided for comparison.")

        comparison_id = str(uuid.uuid4())
        started_at = datetime.now(UTC)
        start_time = time.time()

        logger.info(
            "comparison_starting",
            comparison_id=comparison_id,
            models=models,
            profile=profile,
            probes=probe_names,
            detectors=detector_names,
        )

        # Launch all model scans concurrently
        tasks = [
            self._run_model_scan(
                model_name=model,
                profile=profile,
                probe_names=probe_names,
                detector_names=detector_names,
            )
            for model in models
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Collect successful results and log failures
        scan_results: dict[str, ScanResult] = {}
        for model, result in zip(models, results):
            if isinstance(result, BaseException):
                logger.error(
                    "model_scan_failed",
                    model=model,
                    error=str(result),
                )
            else:
                scan_results[model] = result

        # Build leaderboard from successful results
        leaderboard = self._build_leaderboard(scan_results)

        elapsed_ms = (time.time() - start_time) * 1000
        completed_at = datetime.now(UTC)

        logger.info(
            "comparison_complete",
            comparison_id=comparison_id,
            models_evaluated=len(scan_results),
            models_failed=len(models) - len(scan_results),
            duration_ms=f"{elapsed_ms:.0f}",
        )

        return ComparisonResult(
            comparison_id=comparison_id,
            models=models,
            scan_results=scan_results,
            leaderboard=leaderboard,
            started_at=started_at,
            completed_at=completed_at,
            duration_ms=elapsed_ms,
            metadata={
                "profile": profile,
                "probe_names": probe_names,
                "detector_names": detector_names,
                "models_succeeded": list(scan_results.keys()),
                "models_failed": [
                    m
                    for m, r in zip(models, results)
                    if isinstance(r, BaseException)
                ],
            },
        )

    async def _run_model_scan(
        self,
        model_name: str,
        profile: str | None,
        probe_names: list[str] | None,
        detector_names: list[str] | None,
    ) -> ScanResult:
        """Create a per-model config and execute the scan."""
        model_config = deepcopy(self.base_config)
        model_config.provider.model = model_name

        runner = ScanRunner(model_config)
        return await runner.run(
            profile=profile,
            probe_names=probe_names,
            detector_names=detector_names,
            checkpoint_enabled=False,
        )

    def _build_leaderboard(
        self,
        scan_results: dict[str, ScanResult],
    ) -> list[ModelScore]:
        """Build a ranked leaderboard from scan results.

        Extracts the security score, pass rate, and finding counts from
        each :class:`ScanResult` and returns a list of :class:`ModelScore`
        entries sorted by ``overall_score`` descending (highest/best first).
        """
        scores: list[ModelScore] = []

        for model_name, result in scan_results.items():
            total_findings = len(result.findings)
            failed_findings = sum(1 for f in result.findings if not f.passed)
            pass_rate = (
                round(
                    ((total_findings - failed_findings) / total_findings) * 100,
                    2,
                )
                if total_findings > 0
                else 100.0
            )

            scores.append(
                ModelScore(
                    model_name=model_name,
                    overall_score=result.security_score.overall_score,
                    category_scores=dict(result.security_score.category_scores),
                    risk_level=result.security_score.risk_level,
                    pass_rate=pass_rate,
                    total_findings=total_findings,
                    failed_findings=failed_findings,
                )
            )

        # Sort by overall_score descending (higher is better)
        scores.sort(key=lambda s: s.overall_score, reverse=True)
        return scores
