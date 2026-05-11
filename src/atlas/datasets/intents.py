"""Loader for the shared experiment intent dataset."""
from __future__ import annotations

from atlas.core.models import Intent
from atlas.datasets.manager import DatasetManager

_INTENTS_FILE = "experiment_intents.json"
_BOK_VARIANTS_FILE = "bok_variants.json"


class IntentLoader:
    """Loads and provides access to the canonical experiment intents."""

    def __init__(self, dataset_manager: DatasetManager | None = None) -> None:
        self._dm = dataset_manager or DatasetManager()
        self._intents: list[Intent] | None = None

    def _ensure_loaded(self) -> list[Intent]:
        if self._intents is None:
            raw = self._dm.load_json(_INTENTS_FILE)
            # Merge pre-generated BoK variants if available
            try:
                bok = self._dm.load_json(_BOK_VARIANTS_FILE)
            except Exception:
                bok = {}
            for item in raw:
                if item["id"] in bok:
                    item["bok_variants"] = bok[item["id"]]
            self._intents = [Intent(**item) for item in raw]
        return self._intents

    def load_intents(self) -> list[Intent]:
        """Return all experiment intents."""
        return list(self._ensure_loaded())

    def get_intent(self, intent_id: str) -> Intent:
        """Return a single intent by ID, raising KeyError if not found."""
        for intent in self._ensure_loaded():
            if intent.id == intent_id:
                return intent
        raise KeyError(f"Intent not found: {intent_id}")

    def get_intents_by_category(self, category: str) -> list[Intent]:
        """Return all intents matching the given category."""
        return [i for i in self._ensure_loaded() if i.category == category]
