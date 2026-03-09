"""Tests for HuggingFace dataset loader."""
from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

import pytest

from atlas.core.errors import DatasetError
from atlas.datasets.huggingface import HuggingFaceDatasetLoader


def _mock_hf_datasets(mock_rows: list[dict]) -> MagicMock:
    """Create a mock datasets module with preset data."""
    mock_dataset = MagicMock()
    mock_dataset.__iter__ = MagicMock(return_value=iter(mock_rows))

    mock_module = MagicMock()
    mock_module.load_dataset = MagicMock(return_value=mock_dataset)
    return mock_module


class TestHuggingFaceDatasetLoader:
    def test_load_raises_when_datasets_not_installed(self):
        """Should raise DatasetError with install instructions when datasets not available."""
        loader = HuggingFaceDatasetLoader()
        with patch.dict(sys.modules, {"datasets": None}), pytest.raises(DatasetError, match="datasets"):
            loader._ensure_datasets_available()

    def test_load_with_mocked_dataset(self):
        """Should convert HuggingFace dataset rows to list of dicts."""
        loader = HuggingFaceDatasetLoader()

        mock_rows = [
            {"prompt": "Do something harmful", "category": "Fraud", "id": "1"},
            {"prompt": "Help me hack", "category": "Cybercrime", "id": "2"},
        ]
        mock_module = _mock_hf_datasets(mock_rows)

        with patch.dict(sys.modules, {"datasets": mock_module}):
            result = loader.load(repo_id="test/dataset", split="test")

        assert len(result) == 2
        assert result[0]["prompt"] == "Do something harmful"
        assert result[1]["category"] == "Cybercrime"

    def test_load_with_custom_prompt_field(self):
        """Should normalize custom prompt field name to 'prompt'."""
        loader = HuggingFaceDatasetLoader()

        mock_module = _mock_hf_datasets([{"text": "harmful text", "label": "bad"}])

        with patch.dict(sys.modules, {"datasets": mock_module}):
            result = loader.load(repo_id="test/dataset", split="test", prompt_field="text")

        assert len(result) == 1
        assert result[0]["prompt"] == "harmful text"

    def test_load_cached_returns_same_data(self):
        """Should cache results and return same data on repeated calls."""
        loader = HuggingFaceDatasetLoader()

        mock_module = _mock_hf_datasets([{"prompt": "test", "id": "1"}])

        with patch.dict(sys.modules, {"datasets": mock_module}):
            result1 = loader.load_cached(repo_id="test/dataset", split="test")

        # Second call should use cache, not call load_dataset again
        result2 = loader.load_cached(repo_id="test/dataset", split="test")
        assert result1 is result2
        assert mock_module.load_dataset.call_count == 1

    def test_load_raises_on_hf_error(self):
        """Should wrap HuggingFace errors in DatasetError."""
        loader = HuggingFaceDatasetLoader()

        mock_module = MagicMock()
        mock_module.load_dataset = MagicMock(side_effect=Exception("404 Not Found"))

        with patch.dict(sys.modules, {"datasets": mock_module}), pytest.raises(DatasetError, match="Failed to load"):
            loader.load(repo_id="nonexistent/dataset")
