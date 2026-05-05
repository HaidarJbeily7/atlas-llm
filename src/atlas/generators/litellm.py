"""Universal LLM generator using LiteLLM."""
from __future__ import annotations

import asyncio
import json
from typing import Any

import litellm

from atlas.core.errors import AtlasConnectionError, AtlasTimeoutError, retry_on_transient_error
from atlas.core.models import Attempt, Message, ToolCall, ToolDefinition
from atlas.core.token_tracking import CostCalculator, TokenAccumulator
from atlas.logging.setup import get_logger
from atlas.plugins.registry import register

logger = get_logger(__name__)

# Suppress litellm's verbose logging
litellm.suppress_debug_info = True
litellm.set_verbose = False


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
        self.accumulator: TokenAccumulator | None = None
        self.last_response_metadata: dict[str, Any] = {}

        logger.info(
            "generator_initialized",
            model=model_name,
            timeout=timeout,
            max_retries=max_retries,
        )

    @classmethod
    def from_config(cls, config: Any) -> LiteLLMGenerator:
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

    def _record_usage(self, response: Any) -> None:
        """Extract token usage from a litellm response and record it."""
        if self.accumulator is None:
            return
        usage = getattr(response, "usage", None)
        if usage is None:
            return
        prompt_tokens = getattr(usage, "prompt_tokens", 0) or 0
        completion_tokens = getattr(usage, "completion_tokens", 0) or 0
        cost = CostCalculator.cost_from_response(response, model=self.model_name)
        self.accumulator.record(prompt_tokens, completion_tokens, cost)

    @staticmethod
    def extract_response_metadata(response: Any) -> dict[str, Any]:
        """Extract all useful metadata from a litellm response.

        Captures finish_reason, model ID, system_fingerprint, and
        token usage details for downstream analysis.
        """
        meta: dict[str, Any] = {}
        try:
            choice = response.choices[0] if response.choices else None
            if choice:
                meta["finish_reason"] = getattr(choice, "finish_reason", None)
                # logprobs (if returned by the provider)
                logprobs = getattr(choice, "logprobs", None)
                if logprobs is not None:
                    meta["has_logprobs"] = True

            # Model actually used (may differ from requested, e.g. routing)
            meta["model_id"] = getattr(response, "model", None)
            meta["system_fingerprint"] = getattr(response, "system_fingerprint", None)

            # Full usage breakdown
            usage = getattr(response, "usage", None)
            if usage:
                meta["prompt_tokens"] = getattr(usage, "prompt_tokens", 0) or 0
                meta["completion_tokens"] = getattr(usage, "completion_tokens", 0) or 0
                meta["total_tokens"] = getattr(usage, "total_tokens", 0) or 0
                # Some providers return extra fields
                for extra_field in ("prompt_tokens_details", "completion_tokens_details",
                                    "cache_read_input_tokens", "cache_creation_input_tokens"):
                    val = getattr(usage, extra_field, None)
                    if val is not None:
                        meta[extra_field] = val
        except Exception:
            pass
        return meta

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
            self._record_usage(response)
            self.last_response_metadata = self.extract_response_metadata(response)
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

    @retry_on_transient_error(max_attempts=3)
    async def generate_conversation(
        self, messages: list[Message], **kwargs: Any
    ) -> str:
        """Generate a response given a full conversation history.

        Args:
            messages: Full message history.
            **kwargs: Additional kwargs passed to litellm.acompletion.

        Returns:
            The model's response text.
        """
        msg_dicts: list[dict[str, Any]] = []
        for msg in messages:
            d: dict[str, Any] = {"role": msg.role, "content": msg.content}
            if msg.name:
                d["name"] = msg.name
            if msg.tool_call_id:
                d["tool_call_id"] = msg.tool_call_id
            msg_dicts.append(d)

        call_kwargs = self._build_kwargs(**kwargs)

        try:
            response = await litellm.acompletion(messages=msg_dicts, **call_kwargs)
            self._record_usage(response)
            self.last_response_metadata = self.extract_response_metadata(response)
            content = response.choices[0].message.content or ""
            logger.debug(
                "conversation_generation_complete",
                model=self.model_name,
                turns=len(messages),
                response_len=len(content),
            )
            return content
        except litellm.exceptions.Timeout as e:
            raise AtlasTimeoutError(
                f"LLM request timed out after {self.timeout}s",
                operation="generate_conversation",
                timeout_seconds=float(self.timeout),
            ) from e
        except Exception as e:
            if "rate_limit" in str(e).lower() or "429" in str(e):
                raise AtlasConnectionError(
                    f"Rate limited by provider: {e}",
                    provider=self.model_name.split("/")[0] if "/" in self.model_name else "unknown",
                ) from e
            raise

    @retry_on_transient_error(max_attempts=3)
    async def generate_with_tools(
        self,
        messages: list[Message],
        tools: list[ToolDefinition],
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Generate a response with tool/function calling support.

        Args:
            messages: Conversation messages.
            tools: Available tool definitions.
            **kwargs: Additional kwargs.

        Returns:
            Dict with 'content' (str), 'tool_calls' (list[ToolCall]).
        """
        msg_dicts: list[dict[str, Any]] = []
        for msg in messages:
            d: dict[str, Any] = {"role": msg.role, "content": msg.content}
            if msg.name:
                d["name"] = msg.name
            if msg.tool_call_id:
                d["tool_call_id"] = msg.tool_call_id
            msg_dicts.append(d)

        # Convert tool definitions to OpenAI format
        tool_dicts = [
            {
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description,
                    "parameters": t.parameters,
                },
            }
            for t in tools
        ]

        call_kwargs = self._build_kwargs(**kwargs)

        try:
            response = await litellm.acompletion(
                messages=msg_dicts, tools=tool_dicts, **call_kwargs
            )
            self._record_usage(response)
            msg = response.choices[0].message
            content = msg.content or ""

            parsed_tool_calls: list[ToolCall] = []
            if hasattr(msg, "tool_calls") and msg.tool_calls:
                for tc in msg.tool_calls:
                    try:
                        args = json.loads(tc.function.arguments) if tc.function.arguments else {}
                    except (json.JSONDecodeError, AttributeError):
                        args = {}
                    parsed_tool_calls.append(
                        ToolCall(
                            id=tc.id or "",
                            function_name=tc.function.name,
                            arguments=args,
                        )
                    )

            logger.debug(
                "tool_generation_complete",
                model=self.model_name,
                content_len=len(content),
                tool_calls=len(parsed_tool_calls),
            )

            return {
                "content": content,
                "tool_calls": parsed_tool_calls,
            }
        except litellm.exceptions.Timeout as e:
            raise AtlasTimeoutError(
                f"LLM request timed out after {self.timeout}s",
                operation="generate_with_tools",
                timeout_seconds=float(self.timeout),
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
        """Generate responses for multiple prompts with concurrency control."""
        semaphore = asyncio.Semaphore(concurrency)

        async def _generate_one(prompt: str) -> str:
            async with semaphore:
                return await self.generate(prompt, system_prompt=system_prompt, **kwargs)

        tasks = [_generate_one(p) for p in prompts]
        return await asyncio.gather(*tasks)

    async def generate_for_attempt(self, attempt: Attempt, **kwargs: Any) -> Attempt:
        """Generate response for an Attempt, filling in the response field."""
        if attempt.images:
            # Multimodal: build content array with image parts
            content_parts: list[dict[str, Any]] = [
                {"type": "text", "text": attempt.prompt}
            ]
            for img in attempt.images:
                content_parts.append({
                    "type": "image_url",
                    "image_url": {"url": img},
                })
            messages_list: list[dict[str, Any]] = []
            if attempt.system_prompt:
                messages_list.append({"role": "system", "content": attempt.system_prompt})
            messages_list.append({"role": "user", "content": content_parts})

            call_kwargs = self._build_kwargs(**kwargs)
            try:
                response = await litellm.acompletion(messages=messages_list, **call_kwargs)
                self._record_usage(response)
                attempt.response = response.choices[0].message.content or ""
                attempt.response_metadata = self.extract_response_metadata(response)
            except Exception as e:
                logger.warning("multimodal_generation_error", error=str(e))
                attempt.response = f"[Error: {e}]"
        elif attempt.tool_definitions:
            # Tool-calling mode
            msgs = [Message(role="user", content=attempt.prompt)]
            if attempt.system_prompt:
                msgs.insert(0, Message(role="system", content=attempt.system_prompt))
            result = await self.generate_with_tools(msgs, attempt.tool_definitions, **kwargs)
            attempt.response = result["content"]
            attempt.tool_calls = result["tool_calls"]
        elif attempt.messages:
            # Conversational mode - use existing message history
            attempt.response = await self.generate_conversation(attempt.messages, **kwargs)
        else:
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
