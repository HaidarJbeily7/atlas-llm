"""HuggingFace dataset loading for ATLAS probes."""
from __future__ import annotations

from typing import Any

from atlas.core.errors import DatasetError


class HuggingFaceDatasetLoader:
    """Load datasets from HuggingFace Hub into Atlas format."""

    def __init__(self) -> None:
        self._cache: dict[str, list[dict[str, Any]]] = {}

    def _ensure_datasets_available(self) -> None:
        """Check that the datasets library is installed."""
        try:
            import datasets  # noqa: F401, PLC0415
        except ImportError as exc:
            raise DatasetError(
                "The 'datasets' library is required for HuggingFace dataset loading. "
                "Install it with: pip install atlas-llm[huggingface]",
                error_code="DATASET_002",
                troubleshooting_tips=[
                    "Install the huggingface extra: pip install atlas-llm[huggingface]",
                    "Or install datasets directly: pip install datasets>=2.0",
                ],
            ) from exc

    def load(
        self,
        repo_id: str,
        config_name: str | None = None,
        split: str = "test",
        prompt_field: str = "prompt",
        category_field: str | None = None,  # noqa: ARG002
    ) -> list[dict[str, Any]]:
        """Load a dataset from HuggingFace Hub.

        Args:
            repo_id: HuggingFace dataset repository ID (e.g., "ai-safety-institute/AgentHarm").
            config_name: Dataset configuration/subset name.
            split: Dataset split to load (default: "test").
            prompt_field: Field name containing the prompt text.
            category_field: Optional field name for category information (reserved for future use).

        Returns:
            List of dicts, each containing at least a "prompt" key.
        """
        self._ensure_datasets_available()
        import datasets as hf_datasets  # noqa: PLC0415

        try:
            kwargs: dict[str, Any] = {"path": repo_id, "split": split}
            if config_name:
                kwargs["name"] = config_name
            ds = hf_datasets.load_dataset(**kwargs)
        except Exception as e:
            raise DatasetError(
                f"Failed to load HuggingFace dataset '{repo_id}': {e}",
                error_code="DATASET_003",
                troubleshooting_tips=[
                    f"Verify the dataset exists: https://huggingface.co/datasets/{repo_id}",
                    f"Check that split '{split}' is available",
                    "Ensure you have internet connectivity",
                ],
            ) from e

        results: list[dict[str, Any]] = []
        for row in ds:
            record: dict[str, Any] = dict(row)
            # Normalize prompt field
            if prompt_field in record and prompt_field != "prompt":
                record["prompt"] = record[prompt_field]
            results.append(record)

        return results

    def load_cached(
        self,
        repo_id: str,
        config_name: str | None = None,
        split: str = "test",
        prompt_field: str = "prompt",
        category_field: str | None = None,
    ) -> list[dict[str, Any]]:
        """Load a dataset with in-memory caching.

        Same parameters as load(). Returns cached results on subsequent calls
        with identical parameters.
        """
        cache_key = f"{repo_id}:{config_name}:{split}:{prompt_field}:{category_field}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        data = self.load(
            repo_id=repo_id,
            config_name=config_name,
            split=split,
            prompt_field=prompt_field,
            category_field=category_field,
        )
        self._cache[cache_key] = data
        return data
