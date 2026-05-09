"""Token usage tracking and cost calculation for ATLAS experiments."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from atlas.core.models import Attempt


@dataclass
class TokenAccumulator:
    """Accumulates token usage across multiple LLM calls.

    Attach to a generator to track usage. Use ``role`` to distinguish
    target-model tokens from attacker-model tokens.
    """

    role: str = "target"  # "target" or "attacker"
    tokens_in: int = 0
    tokens_out: int = 0
    cost_usd: float = 0.0
    num_calls: int = 0

    def record(
        self,
        prompt_tokens: int,
        completion_tokens: int,
        cost: float = 0.0,
    ) -> None:
        """Record usage from a single API call."""
        self.tokens_in += prompt_tokens
        self.tokens_out += completion_tokens
        self.cost_usd += cost
        self.num_calls += 1

    def apply_to(self, attempt: Attempt) -> None:
        """Flush accumulated counts onto an Attempt model."""
        if self.role == "target":
            attempt.target_tokens_in += self.tokens_in
            attempt.target_tokens_out += self.tokens_out
            attempt.num_target_calls += self.num_calls
        else:
            attempt.attacker_tokens_in += self.tokens_in
            attempt.attacker_tokens_out += self.tokens_out
            attempt.num_attacker_calls += self.num_calls
        attempt.cost_usd += self.cost_usd

    def reset(self) -> None:
        """Reset all counters."""
        self.tokens_in = 0
        self.tokens_out = 0
        self.cost_usd = 0.0
        self.num_calls = 0


class CostCalculator:
    """Calculate USD cost from token usage.

    Prefers litellm's built-in pricing when available, falling back
    to a static table.
    """

    # Fallback pricing: model prefix -> (input $/1K tokens, output $/1K tokens)
    # Used when litellm's built-in pricing lookup fails (e.g. newer models
    # or provider-prefixed names not yet in litellm's cost map).
    PRICING: dict[str, tuple[float, float]] = {
        # OpenAI
        "openai/gpt-4o-mini": (0.00015, 0.0006),
        "openai/gpt-4o": (0.0025, 0.01),
        "openai/gpt-4-turbo": (0.01, 0.03),
        # Anthropic
        "anthropic/claude-sonnet-4": (0.003, 0.015),
        "anthropic/claude-4-sonnet": (0.003, 0.015),
        "anthropic/claude-3-5-sonnet": (0.003, 0.015),
        "anthropic/claude-3-opus": (0.015, 0.075),
        "anthropic/claude-3-haiku": (0.00025, 0.00125),
        # Google
        "google/gemini-2.5-flash": (0.0003, 0.0025),
        "google/gemini-pro": (0.000125, 0.000375),
        "google/gemini-1.5-pro": (0.00125, 0.005),
        # Meta Llama
        "meta-llama/llama-3.3-70b-instruct": (0.00023, 0.0004),
        "meta-llama/llama-3.1-70b-instruct": (0.00023, 0.0004),
        # Mistral
        "mistralai/mistral-large": (0.002, 0.006),
        # Qwen
        "qwen/qwen-2.5-72b-instruct": (0.00035, 0.0004),
        # DeepSeek
        "deepseek/deepseek-chat": (0.00014, 0.00028),
        "deepseek/deepseek-r1": (0.00055, 0.00219),
    }

    @classmethod
    def _strip_router_prefix(cls, model: str) -> str:
        """Strip routing prefixes (e.g. 'openrouter/') to get the canonical model name."""
        router_prefixes = ("openrouter/",)
        for prefix in router_prefixes:
            if model.startswith(prefix):
                return model[len(prefix):]
        return model

    @classmethod
    def calculate(cls, model: str, tokens_in: int, tokens_out: int) -> float:
        """Compute USD cost for a given model and token counts."""
        # Try litellm's built-in cost calculation, stripping router prefix if needed
        for candidate in dict.fromkeys([model, cls._strip_router_prefix(model)]):
            try:
                import litellm
                prompt_cost, completion_cost = litellm.cost_per_token(
                    model=candidate,
                    prompt_tokens=tokens_in,
                    completion_tokens=tokens_out,
                )
                return prompt_cost + completion_cost
            except Exception:
                continue

        # Fallback to static table (prefix match against canonical name)
        canonical = cls._strip_router_prefix(model)
        for prefix, (in_price, out_price) in cls.PRICING.items():
            if canonical.startswith(prefix):
                return (tokens_in * in_price / 1000) + (
                    tokens_out * out_price / 1000
                )

        return 0.0

    @classmethod
    def cost_from_response(cls, response: Any, model: str | None = None) -> float:
        """Extract cost from a litellm response object if available."""
        try:
            import litellm
            return litellm.completion_cost(completion_response=response)
        except Exception:
            pass

        # Fallback: calculate from usage on the response
        usage = getattr(response, "usage", None)
        if usage and model:
            prompt_tokens = getattr(usage, "prompt_tokens", 0) or 0
            completion_tokens = getattr(usage, "completion_tokens", 0) or 0
            if prompt_tokens or completion_tokens:
                return cls.calculate(model, prompt_tokens, completion_tokens)

        return 0.0
