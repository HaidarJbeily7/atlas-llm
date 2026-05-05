"""Base probe classes for ATLAS security probes."""
from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from typing import Any

from atlas.core.enums import VulnerabilityCategory
from atlas.core.models import Attempt, Message
from atlas.datasets.manager import DatasetManager
from atlas.logging.setup import get_logger

logger = get_logger(__name__)


class BaseProbe(ABC):
    """Abstract base for all security probes.

    Subclasses must set name, category, tags and implement generate_prompts().
    """

    name: str = ""
    category: VulnerabilityCategory = VulnerabilityCategory.OTHER
    description: str = ""
    tags: list[str] = []
    recommended_detector: str = "keyword"

    def __init__(self, dataset_manager: DatasetManager | None = None) -> None:
        self.dataset_manager = dataset_manager or DatasetManager()

    @abstractmethod
    def generate_prompts(self) -> list[Attempt]:
        """Generate probe attempts (prompts to test the model with)."""
        ...

    def _make_attempt(self, prompt: str, **metadata: Any) -> Attempt:
        """Helper to create an Attempt with standard fields."""
        return Attempt(
            probe_name=self.name,
            prompt=prompt,
            tags=list(self.tags),
            metadata={"category": self.category.value, **metadata},
        )

    @staticmethod
    async def _retry_target_call(
        generator: Any,
        messages: list[Message],
        max_retries: int = 2,
    ) -> str:
        """Call generator.generate_conversation with retry + backoff.

        Raises the last exception if all retries are exhausted.
        """
        last_exc: Exception | None = None
        for attempt_num in range(max_retries + 1):
            try:
                return await generator.generate_conversation(messages=messages)
            except Exception as exc:
                last_exc = exc
                if attempt_num < max_retries:
                    wait = 1.0 * (attempt_num + 1)
                    logger.warning(
                        "target_call_retry",
                        attempt=attempt_num + 1,
                        max_retries=max_retries,
                        error=str(exc),
                        wait_s=wait,
                    )
                    await asyncio.sleep(wait)
        raise last_exc  # type: ignore[misc]


class ConversationalProbe(BaseProbe):
    """Base class for multi-turn conversational probes.

    Subclasses implement run_conversation() which drives a multi-turn
    interaction with the target LLM through the generator.
    """

    max_turns: int = 5
    is_conversational: bool = True

    @abstractmethod
    async def run_conversation(self, generator: Any, attempt: Attempt) -> Attempt:
        """Drive a multi-turn conversation and return the final attempt.

        Args:
            generator: The LLM generator to interact with.
            attempt: Initial attempt with the seed prompt.

        Returns:
            The attempt with full conversation in messages and final response.
        """
        ...

    def _add_message(self, attempt: Attempt, role: str, content: str) -> None:
        """Append a message to the attempt's conversation history."""
        attempt.messages.append(Message(role=role, content=content))

    def _check_stop_condition(self, response: str) -> bool:
        """Check if the conversation should stop (override in subclass)."""
        return False


class AdaptiveProbe(BaseProbe):
    """Base class for adaptive probes that use an attacker LLM.

    These probes use a separate 'attacker' model to generate
    adversarial prompts based on the target model's responses.
    """

    max_iterations: int = 10
    is_adaptive: bool = True
    attacker_model: str = ""

    @abstractmethod
    async def run_adaptive_attack(
        self,
        target_generator: Any,
        attacker_generator: Any,
        attempt: Attempt,
    ) -> Attempt:
        """Run an adaptive attack using attacker LLM to refine prompts.

        Args:
            target_generator: The target LLM generator.
            attacker_generator: The attacker LLM generator.
            attempt: Initial attempt with the objective.

        Returns:
            The attempt with the best adversarial result.
        """
        ...
