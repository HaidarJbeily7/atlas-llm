"""Async concurrency scheduler for ATLAS scan execution."""
from __future__ import annotations

import asyncio
from typing import Any, Awaitable, Callable, TypeVar

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
