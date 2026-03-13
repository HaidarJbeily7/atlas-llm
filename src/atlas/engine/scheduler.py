"""Async concurrency scheduler for ATLAS scan execution."""
from __future__ import annotations

import asyncio
import time
from typing import Any, Awaitable, TypeVar

from atlas.logging.setup import get_logger

logger = get_logger(__name__)

T = TypeVar("T")


class AsyncScheduler:
    """Semaphore-based async concurrency controller."""

    def __init__(self, concurrency: int = 10) -> None:
        self.concurrency = concurrency
        self._semaphore = asyncio.Semaphore(concurrency)
        self._completed = 0
        self._failed = 0
        self._total = 0

    async def run_task(self, coro: Awaitable[T]) -> T:
        """Run a single coroutine with semaphore control."""
        async with self._semaphore:
            try:
                result = await coro
                self._completed += 1
                return result
            except Exception:
                self._failed += 1
                raise

    async def run_batch(
        self,
        tasks: list[Awaitable[T]],
        continue_on_error: bool = False,
    ) -> list[T | Exception]:
        """Run a batch of coroutines with concurrency control.

        Args:
            tasks: List of awaitables to execute.
            continue_on_error: If True, collect exceptions instead of raising.

        Returns:
            List of results (or Exception objects if continue_on_error).
        """
        self._total = len(tasks)
        self._completed = 0
        self._failed = 0

        async def _wrap(task: Awaitable[T]) -> T | Exception:
            try:
                return await self.run_task(task)
            except Exception as e:
                if continue_on_error:
                    logger.warning("task_failed", error=str(e))
                    return e
                raise

        if continue_on_error:
            results = await asyncio.gather(*[_wrap(t) for t in tasks], return_exceptions=True)
        else:
            results = await asyncio.gather(*[_wrap(t) for t in tasks])

        logger.info(
            "batch_complete",
            total=self._total,
            completed=self._completed,
            failed=self._failed,
        )
        return results

    @property
    def stats(self) -> dict[str, int]:
        return {
            "total": self._total,
            "completed": self._completed,
            "failed": self._failed,
            "pending": self._total - self._completed - self._failed,
        }


class _TokenBucketRateLimiter:
    """Token-bucket rate limiter for per-model request throttling.

    Allows up to ``capacity`` requests, refilling at ``refill_rate``
    tokens per second.
    """

    def __init__(self, capacity: int = 60, refill_rate: float = 10.0) -> None:
        self.capacity = capacity
        self.refill_rate = refill_rate
        self._tokens = float(capacity)
        self._last_refill: float = 0.0
        self._lock = asyncio.Lock()
        self._initialized = False

    async def acquire(self) -> None:
        """Wait until a token is available, then consume one."""
        while True:
            async with self._lock:
                now = asyncio.get_event_loop().time()
                if not self._initialized:
                    self._last_refill = now
                    self._initialized = True

                elapsed = now - self._last_refill
                self._tokens = min(
                    self.capacity,
                    self._tokens + elapsed * self.refill_rate,
                )
                self._last_refill = now

                if self._tokens >= 1.0:
                    self._tokens -= 1.0
                    return

            # No tokens available -- back off briefly before retrying
            await asyncio.sleep(1.0 / self.refill_rate)


class ParallelModelScheduler:
    """Run the same scan against multiple models concurrently.

    This scheduler creates a separate :class:`ScanRunner` for each model,
    applies per-model rate limiting, and collects all results into a dict
    keyed by model name.

    Example::

        scheduler = ParallelModelScheduler(
            model_names=["openai/gpt-4o", "anthropic/claude-3-opus"],
            base_config=my_config,
        )
        results = await scheduler.run(profile="standard")
        for model, result in results.items():
            print(model, result.security_score.overall_score)
    """

    def __init__(
        self,
        model_names: list[str],
        base_config: "AtlasConfig",
        *,
        requests_per_minute: int = 60,
        per_model_concurrency: int = 10,
    ) -> None:
        from atlas.config.models import AtlasConfig  # noqa: F811 (deferred import)

        if not model_names:
            raise ValueError("model_names must contain at least one model")

        self.model_names = list(model_names)
        self.base_config = base_config
        self.per_model_concurrency = per_model_concurrency

        # Create a rate limiter per model
        refill_rate = requests_per_minute / 60.0
        self._rate_limiters: dict[str, _TokenBucketRateLimiter] = {
            name: _TokenBucketRateLimiter(
                capacity=requests_per_minute,
                refill_rate=refill_rate,
            )
            for name in self.model_names
        }

        self._results: dict[str, Any] = {}
        self._errors: dict[str, Exception] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def run(
        self,
        profile: str | None = None,
        probe_names: list[str] | None = None,
        detector_names: list[str] | None = None,
        continue_on_error: bool = True,
    ) -> dict[str, "ScanResult"]:
        """Execute the scan against every model in parallel.

        Args:
            profile: Named scan profile (e.g. ``"standard"``, ``"comprehensive"``).
            probe_names: Explicit list of probes to run (overrides profile).
            detector_names: Explicit list of detectors to use.
            continue_on_error: If ``True``, failures for one model do not
                cancel the remaining models.

        Returns:
            Mapping of *model_name* to its :class:`ScanResult`.  Models that
            failed are excluded from the dict; call :pyattr:`errors` to
            inspect failures.
        """
        from atlas.core.models import ScanResult  # deferred import

        start = time.time()

        logger.info(
            "parallel_scan_starting",
            models=self.model_names,
            profile=profile,
        )

        tasks = [
            self._run_single_model(
                model_name=model,
                profile=profile,
                probe_names=probe_names,
                detector_names=detector_names,
            )
            for model in self.model_names
        ]

        raw_results = await asyncio.gather(*tasks, return_exceptions=True)

        results: dict[str, ScanResult] = {}
        errors: dict[str, Exception] = {}

        for model, result in zip(self.model_names, raw_results):
            if isinstance(result, Exception):
                errors[model] = result
                logger.error(
                    "model_scan_failed",
                    model=model,
                    error=str(result),
                )
                if not continue_on_error:
                    raise result
            else:
                results[model] = result

        self._results = results
        self._errors = errors

        elapsed_ms = (time.time() - start) * 1000
        logger.info(
            "parallel_scan_complete",
            total_models=len(self.model_names),
            succeeded=len(results),
            failed=len(errors),
            duration_ms=f"{elapsed_ms:.0f}",
        )

        return results

    @property
    def errors(self) -> dict[str, Exception]:
        """Models that failed during the most recent :meth:`run`."""
        return dict(self._errors)

    @property
    def stats(self) -> dict[str, Any]:
        """Summary statistics for the most recent run."""
        return {
            "total_models": len(self.model_names),
            "succeeded": len(self._results),
            "failed": len(self._errors),
            "failed_models": list(self._errors.keys()),
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_config_for_model(self, model_name: str) -> "AtlasConfig":
        """Clone the base config with a different model name."""
        config_data = self.base_config.model_dump()
        config_data["provider"]["model"] = model_name
        config_data["scan"]["concurrency"] = self.per_model_concurrency

        from atlas.config.models import AtlasConfig  # deferred import

        return AtlasConfig.model_validate(config_data)

    async def _run_single_model(
        self,
        model_name: str,
        profile: str | None,
        probe_names: list[str] | None,
        detector_names: list[str] | None,
    ) -> "ScanResult":
        """Run a scan for a single model, respecting its rate limiter."""
        from atlas.engine.runner import ScanRunner  # deferred import

        model_config = self._build_config_for_model(model_name)
        runner = ScanRunner(model_config)

        # Wrap the generator's completion call with rate-limiting
        rate_limiter = self._rate_limiters[model_name]
        original_generate = runner.generator.generate

        async def _rate_limited_generate(*args: Any, **kwargs: Any) -> Any:
            await rate_limiter.acquire()
            return await original_generate(*args, **kwargs)

        runner.generator.generate = _rate_limited_generate  # type: ignore[assignment]

        logger.info("model_scan_starting", model=model_name)

        result = await runner.run(
            profile=profile,
            probe_names=probe_names,
            detector_names=detector_names,
            checkpoint_enabled=True,
        )

        logger.info(
            "model_scan_complete",
            model=model_name,
            score=f"{result.security_score.overall_score:.1f}",
            risk_level=result.security_score.risk_level.value,
        )

        return result
