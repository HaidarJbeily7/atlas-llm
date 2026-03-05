"""Universal LLM generator using LiteLLM."""
from __future__ import annotations

import asyncio
from typing import Any

import litellm

from atlas.core.errors import AtlasConnectionError, AtlasTimeoutError, retry_on_transient_error
from atlas.core.models import Attempt
from atlas.logging.setup import get_logger
from atlas.plugins.registry import register

logger = get_logger(__name__)

# Suppress litellm's verbose logging
litellm.suppress_debug_info = True


@register("generators", name="litellm")
class LiteLLMGenerator:
    """Universal LLM generator backed by LiteLLM.

    Supports all providers via LiteLLM's model string format:
    - openai/gpt-4o, openai/gpt-4o-mini
    - anthropic/claude-3-opus-20240229
    - google/gemini-pro
    - azure/my-deployment
    - huggingface/meta-llama/Llama-2-7b
    - openrouter/meta-llama/llama-3-70b
    """

    def __init__(
        self,
        model_name: str,
        api_key: str | None = None,
        api_base: str | None = None,
        timeout: int = 30,
        max_retries: int = 3,
        temperature: float = 0.0,
        max_tokens: int | None = None,
        extra: dict[str, Any] | None = None,
    ) -> None:
        self.model_name = model_name
        self.api_key = api_key
        self.api_base = api_base
        self.timeout = timeout
        self.max_retries = max_retries
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.extra = extra or {}

        logger.info(
            "generator_initialized",
            model=model_name,
            timeout=timeout,
            max_retries=max_retries,
        )

    @classmethod
    def from_config(cls, config) -> LiteLLMGenerator:
        """Create generator from ProviderConfig."""
        return cls(
            model_name=config.model,
            api_key=config.api_key,
            api_base=config.api_base,
            timeout=config.timeout,
            max_retries=config.max_retries,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
            extra=config.extra,
        )

    def _build_kwargs(self, **overrides: Any) -> dict[str, Any]:
        """Build keyword arguments for litellm.acompletion."""
        kwargs: dict[str, Any] = {
            "model": self.model_name,
            "temperature": self.temperature,
            "timeout": self.timeout,
            "num_retries": self.max_retries,
        }
        if self.api_key:
            kwargs["api_key"] = self.api_key
        if self.api_base:
            kwargs["api_base"] = self.api_base
        if self.max_tokens:
            kwargs["max_tokens"] = self.max_tokens
        kwargs.update(self.extra)
        kwargs.update(overrides)
        return kwargs

    @retry_on_transient_error(max_attempts=3)
    async def generate(self, prompt: str, system_prompt: str = "", **kwargs: Any) -> str:
        """Generate a single response from the LLM.

        Args:
            prompt: The user prompt to send.
            system_prompt: Optional system prompt.
            **kwargs: Additional kwargs passed to litellm.acompletion.

        Returns:
            The model's response text.
        """
        messages: list[dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        call_kwargs = self._build_kwargs(**kwargs)

        try:
            response = await litellm.acompletion(messages=messages, **call_kwargs)
            content = response.choices[0].message.content or ""
            logger.debug(
                "generation_complete",
                model=self.model_name,
                prompt_len=len(prompt),
                response_len=len(content),
            )
            return content
        except litellm.exceptions.Timeout as e:
            raise AtlasTimeoutError(
                f"LLM request timed out after {self.timeout}s",
                operation="generate",
                timeout_seconds=float(self.timeout),
            ) from e
        except (litellm.exceptions.AuthenticationError, litellm.exceptions.BadRequestError) as e:
            raise AtlasConnectionError(
                f"LLM provider error: {e}",
                provider=self.model_name.split("/")[0] if "/" in self.model_name else "unknown",
            ) from e
        except Exception as e:
            if "rate_limit" in str(e).lower() or "429" in str(e):
                raise AtlasConnectionError(
                    f"Rate limited by provider: {e}",
                    provider=self.model_name.split("/")[0] if "/" in self.model_name else "unknown",
                ) from e
            raise

    async def generate_batch(
        self,
        prompts: list[str],
        system_prompt: str = "",
        concurrency: int = 5,
        **kwargs: Any,
    ) -> list[str]:
        """Generate responses for multiple prompts with concurrency control.

        Args:
            prompts: List of prompts.
            system_prompt: Optional system prompt applied to all.
            concurrency: Max concurrent requests.
            **kwargs: Additional kwargs passed to litellm.acompletion.

        Returns:
            List of response texts (in same order as prompts).
        """
        semaphore = asyncio.Semaphore(concurrency)

        async def _generate_one(prompt: str) -> str:
            async with semaphore:
                return await self.generate(prompt, system_prompt=system_prompt, **kwargs)

        tasks = [_generate_one(p) for p in prompts]
        return await asyncio.gather(*tasks)

    async def generate_for_attempt(self, attempt: Attempt, **kwargs: Any) -> Attempt:
        """Generate response for an Attempt, filling in the response field.

        Args:
            attempt: Attempt with prompt (and optional system_prompt).
            **kwargs: Additional kwargs passed to litellm.acompletion.

        Returns:
            The same Attempt with response filled in.
        """
        response = await self.generate(
            attempt.prompt,
            system_prompt=attempt.system_prompt,
            **kwargs,
        )
        attempt.response = response
        return attempt

    async def generate_for_attempts(
        self,
        attempts: list[Attempt],
        concurrency: int = 5,
        **kwargs: Any,
    ) -> list[Attempt]:
        """Generate responses for multiple Attempts with concurrency control."""
        semaphore = asyncio.Semaphore(concurrency)

        async def _gen(attempt: Attempt) -> Attempt:
            async with semaphore:
                return await self.generate_for_attempt(attempt, **kwargs)

        tasks = [_gen(a) for a in attempts]
        return await asyncio.gather(*tasks)
