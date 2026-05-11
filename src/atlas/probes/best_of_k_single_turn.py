"""Best-of-K non-adaptive single-turn probe for the 2x2 factorial experiment.

Sends K=5 pre-generated adversarial prompt variants to the target model
independently (one attempt per variant). No attacker LLM is used at
runtime — all variants were generated offline before the experiment via
``scripts/generate_bok_variants.py``.

This is the matched-budget non-adaptive control for ``adaptive_single_turn``
(PAIR with K=5 iterations). Both conditions use up to 5 target queries per
intent, but BoK generates all variants upfront without seeing any target
responses, while PAIR refines iteratively with feedback.

Success criterion: an intent is "jailbroken" if ANY of the K variants
succeeds (evaluated independently by detectors, aggregated in analysis).

This module is intended for authorized security research and testing only.
"""
from __future__ import annotations

from atlas.core.enums import VulnerabilityCategory
from atlas.core.models import Attempt
from atlas.datasets.intents import IntentLoader
from atlas.logging.setup import get_logger
from atlas.plugins.registry import register
from atlas.probes.base import BaseProbe

logger = get_logger(__name__)


@register("probes", name="best_of_k_st")
class BestOfKSingleTurnProbe(BaseProbe):
    """Best-of-K non-adaptive single-turn baseline.

    Loads K pre-generated prompt variants per intent and creates one
    attempt for each variant. Each attempt is sent to the target model
    independently (no conversation context between variants). The
    analysis pipeline aggregates results per intent: the intent counts
    as "jailbroken" if any of its K variants bypasses safety.

    Attributes:
        k: Number of variants per intent (default 5, matching
            adaptive_single_turn's iteration budget).
    """

    name = "best_of_k_st"
    category = VulnerabilityCategory.JAILBREAK
    description = (
        "Best-of-K non-adaptive baseline — sends K=5 pre-generated diverse "
        "prompt variants to the target independently, with no feedback loop. "
        "Matched target-query budget with adaptive_single_turn for fair comparison."
    )
    tags = [
        "owasp:llm01",
        "eu-ai-act:article-15-5",
        "single-turn",
        "non-adaptive",
        "baseline",
        "experiment",
    ]
    recommended_detector = "keyword"
    k = 5

    def generate_prompts(self) -> list[Attempt]:
        """Generate K attempts per intent from pre-generated BoK variants.

        Returns 40 × K = 200 attempts (for K=5). Each attempt carries
        metadata identifying the parent intent and variant index so
        the analysis pipeline can aggregate per-intent results.
        """
        loader = IntentLoader(self.dataset_manager)
        intents = loader.load_intents()
        attempts: list[Attempt] = []

        for intent in intents:
            variants = intent.bok_variants or [intent.direct_prompt]

            for variant_idx, variant_prompt in enumerate(variants[: self.k]):
                attempt = self._make_attempt(
                    prompt=variant_prompt,
                    source="best_of_k_st",
                    intent_id=intent.id,
                    objective=intent.objective,
                    condition="best_of_k_st",
                    adaptivity="none",
                    interaction_mode="single_turn",
                    k=self.k,
                    variant_index=variant_idx,
                    total_variants=len(variants[: self.k]),
                )
                attempts.append(attempt)

        logger.info(
            "best_of_k_st_prompts_generated",
            total_attempts=len(attempts),
            intents=len(intents),
            k=self.k,
        )

        return attempts
