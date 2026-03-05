"""Base probe class for ATLAS security probes."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from atlas.core.enums import VulnerabilityCategory
from atlas.core.models import Attempt
from atlas.datasets.manager import DatasetManager


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
