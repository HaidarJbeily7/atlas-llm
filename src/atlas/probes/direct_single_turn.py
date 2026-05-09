"""Direct single-turn baseline probe for the experiment.

Sends each intent's ``direct_prompt`` verbatim to the target model —
no attacker LLM, no jailbreak templates, no conversation.  Produces
exactly 40 findings (one per intent) on the same intent set used by
all adaptive conditions, enabling paired statistical comparisons.
"""
from __future__ import annotations

from atlas.core.enums import VulnerabilityCategory
from atlas.core.models import Attempt
from atlas.datasets.intents import IntentLoader
from atlas.plugins.registry import register
from atlas.probes.base import BaseProbe


@register("probes", name="direct_single_turn")
class DirectSingleTurnProbe(BaseProbe):
    """Direct single-turn baseline — raw harmful request, no jailbreak."""

    name = "direct_single_turn"
    category = VulnerabilityCategory.JAILBREAK
    description = (
        "Sends the raw harmful objective as a plain prompt with no "
        "jailbreak wrapper or attacker optimisation. Serves as the "
        "direct baseline for paired comparison with adaptive conditions."
    )
    tags = [
        "owasp:llm01",
        "eu-ai-act:article-15-5",
        "single-turn",
        "static",
        "baseline",
        "experiment",
    ]
    recommended_detector = "keyword"

    def generate_prompts(self) -> list[Attempt]:
        """Generate one attempt per intent using the raw direct_prompt."""
        loader = IntentLoader(self.dataset_manager)
        intents = loader.load_intents()
        attempts = []

        for intent in intents:
            attempt = self._make_attempt(
                prompt=intent.direct_prompt,
                source="direct_single_turn",
                intent_id=intent.id,
                objective=intent.objective,
                condition="direct_single_turn",
                adaptivity="none",
                interaction_mode="single_turn",
            )
            attempts.append(attempt)

        return attempts
