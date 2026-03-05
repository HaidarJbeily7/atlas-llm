"""Tests for dataset manager."""
import json
import pytest
from atlas.core.errors import DatasetError
from atlas.datasets.manager import DatasetManager


class TestDatasetManager:
    def test_load_json(self, dataset_manager):
        data = dataset_manager.load_json("test.json")
        assert data == ["prompt1", "prompt2", "prompt3"]

    def test_load_json_cached(self, dataset_manager):
        data1 = dataset_manager.load_json("test.json")
        data2 = dataset_manager.load_json("test.json")
        assert data1 is data2  # Same object from cache

    def test_load_txt(self, dataset_manager):
        lines = dataset_manager.load_txt("test.txt")
        assert lines == ["line1", "line2", "line3"]

    def test_load_jsonl(self, dataset_manager):
        data = dataset_manager.load_jsonl("test.jsonl")
        assert len(data) == 2
        assert data[0]["prompt"] == "p1"

    def test_load_auto(self, dataset_manager):
        data = dataset_manager.load_auto("test.json")
        assert isinstance(data, list)

    def test_list_datasets(self, dataset_manager):
        datasets = dataset_manager.list_datasets()
        assert len(datasets) >= 3

    def test_list_datasets_by_category(self, dataset_manager):
        datasets = dataset_manager.list_datasets("subdir")
        assert len(datasets) == 1

    def test_missing_file_raises(self, dataset_manager):
        with pytest.raises(DatasetError):
            dataset_manager.load_json("nonexistent.json")

    def test_clear_cache(self, dataset_manager):
        dataset_manager.load_json("test.json")
        assert len(dataset_manager._cache) > 0
        dataset_manager.clear_cache()
        assert len(dataset_manager._cache) == 0
