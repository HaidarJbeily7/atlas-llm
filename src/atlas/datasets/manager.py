"""Dataset loading and management for ATLAS probes."""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from atlas.core.errors import DatasetError

# Root directory for vendored datasets
DATA_DIR = Path(__file__).parent / "data"


class DatasetManager:
    """Loads and caches probe datasets from JSON/JSONL/TXT/YAML files."""

    def __init__(self, data_dir: Path | None = None) -> None:
        self.data_dir = data_dir or DATA_DIR
        self._cache: dict[str, Any] = {}

    def load_json(self, relative_path: str) -> Any:
        """Load a JSON file relative to data_dir."""
        cache_key = f"json:{relative_path}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        path = self.data_dir / relative_path
        if not path.exists():
            raise DatasetError(f"Dataset file not found: {path}")

        try:
            with open(path) as f:
                data = json.load(f)
            self._cache[cache_key] = data
            return data
        except json.JSONDecodeError as e:
            raise DatasetError(f"Invalid JSON in {path}: {e}") from e

    def load_jsonl(self, relative_path: str) -> list[dict[str, Any]]:
        """Load a JSONL file (one JSON object per line)."""
        cache_key = f"jsonl:{relative_path}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        path = self.data_dir / relative_path
        if not path.exists():
            raise DatasetError(f"Dataset file not found: {path}")

        results = []
        try:
            with open(path) as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if line:
                        results.append(json.loads(line))
        except json.JSONDecodeError as e:
            raise DatasetError(f"Invalid JSONL at line {line_num} in {path}: {e}") from e

        self._cache[cache_key] = results
        return results

    def load_txt(self, relative_path: str) -> list[str]:
        """Load a text file, returning non-empty lines."""
        cache_key = f"txt:{relative_path}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        path = self.data_dir / relative_path
        if not path.exists():
            raise DatasetError(f"Dataset file not found: {path}")

        with open(path) as f:
            lines = [line.strip() for line in f if line.strip() and not line.startswith("#")]

        self._cache[cache_key] = lines
        return lines

    def load_yaml(self, relative_path: str) -> Any:
        """Load a YAML file."""
        import yaml

        cache_key = f"yaml:{relative_path}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        path = self.data_dir / relative_path
        if not path.exists():
            raise DatasetError(f"Dataset file not found: {path}")

        with open(path) as f:
            data = yaml.safe_load(f)

        self._cache[cache_key] = data
        return data

    def list_datasets(self, category: str | None = None) -> list[str]:
        """List available dataset files, optionally filtered by category (subdirectory)."""
        if category:
            search_dir = self.data_dir / category
            if not search_dir.is_dir():
                return []
            return sorted(str(p.relative_to(self.data_dir)) for p in search_dir.rglob("*") if p.is_file() and not p.name.startswith("."))

        return sorted(
            str(p.relative_to(self.data_dir))
            for p in self.data_dir.rglob("*")
            if p.is_file() and not p.name.startswith(".") and p.name != "ATTRIBUTION.md"
        )

    def load_auto(self, relative_path: str) -> Any:
        """Auto-detect format and load. Dispatches based on file extension."""
        path = self.data_dir / relative_path
        suffix = path.suffix.lower()

        if suffix == ".json":
            return self.load_json(relative_path)
        elif suffix == ".jsonl":
            return self.load_jsonl(relative_path)
        elif suffix in (".txt", ".csv"):
            return self.load_txt(relative_path)
        elif suffix in (".yaml", ".yml"):
            return self.load_yaml(relative_path)
        else:
            raise DatasetError(f"Unsupported file format: {suffix} for {relative_path}")

    def clear_cache(self) -> None:
        """Clear the dataset cache."""
        self._cache.clear()
