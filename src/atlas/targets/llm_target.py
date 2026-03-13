"""Direct LLM target that wraps a LiteLLMGenerator."""
from __future__ import annotations

from typing import Any

from atlas.core.models import Attempt, Message
from atlas.generators.litellm import LiteLLMGenerator
from atlas.logging.setup import get_logger
from atlas.plugins.registry import register
from atlas.targets.base import BaseTarget

logger = get_logger(__name__)


@register("targets", name="llm")
class LLMTarget(BaseTarget):
    """Target that sends prompts directly to an LLM via :class:`LiteLLMGenerator`.

    This is the simplest target type -- it delegates prompt delivery
    and response retrieval entirely to the underlying generator.

    Args:
        generator: A configured :class:`LiteLLMGenerator` instance.
        name: Human-readable name for this target (defaults to the model name).
    """

    def __init__(
        self,
        generator: LiteLLMGenerator,
        name: str | None = None,
    ) -> None:
        self.generator = generator
        self.name = name or f"llm:{generator.model_name}"

        logger.info(
            "llm_target_initialized",
            name=self.name,
            model=generator.model_name,
        )

    @classmethod
    def from_config(
        cls,
        model_name: str,
        api_key: str | None = None,
        api_base: str | None = None,
        timeout: int = 30,
        max_retries: int = 3,
        temperature: float = 0.0,
        max_tokens: int | None = None,
        extra: dict[str, Any] | None = None,
        name: str | None = None,
    ) -> LLMTarget:
        """Create an LLMTarget from explicit configuration values.

        This is a convenience constructor that builds the underlying
        :class:`LiteLLMGenerator` automatically.

        Args:
            model_name: LiteLLM model string (e.g. ``"openai/gpt-4o"``).
            api_key: Provider API key.
            api_base: Custom API base URL.
            timeout: Request timeout in seconds.
            max_retries: Maximum number of retry attempts.
            temperature: Sampling temperature.
            max_tokens: Maximum response tokens.
            extra: Additional kwargs forwarded to litellm.
            name: Human-readable target name.

        Returns:
            A fully configured :class:`LLMTarget`.
        """
        generator = LiteLLMGenerator(
            model_name=model_name,
            api_key=api_key,
            api_base=api_base,
            timeout=timeout,
            max_retries=max_retries,
            temperature=temperature,
            max_tokens=max_tokens,
            extra=extra,
        )
        return cls(generator=generator, name=name)

    async def send(self, attempt: Attempt) -> Attempt:
        """Send an attempt to the LLM and populate its response.

        Delegates to :meth:`LiteLLMGenerator.generate_for_attempt` which
        handles plain text, conversational, multimodal, and tool-calling
        modes based on the attempt's fields.

        Args:
            attempt: The probe attempt to send.

        Returns:
            The attempt with ``response`` (and possibly ``tool_calls``) filled.
        """
        logger.debug(
            "llm_target_send",
            target=self.name,
            probe=attempt.probe_name,
            prompt_len=len(attempt.prompt),
        )
        attempt = await self.generator.generate_for_attempt(attempt)
        logger.debug(
            "llm_target_response",
            target=self.name,
            response_len=len(attempt.response),
        )
        return attempt

    async def send_messages(self, messages: list[Message]) -> str:
        """Send a conversation to the LLM and return the response.

        Args:
            messages: Ordered list of conversation messages.

        Returns:
            The model's response content.
        """
        logger.debug(
            "llm_target_send_messages",
            target=self.name,
            num_messages=len(messages),
        )
        response = await self.generator.generate_conversation(messages)
        logger.debug(
            "llm_target_messages_response",
            target=self.name,
            response_len=len(response),
        )
        return response
