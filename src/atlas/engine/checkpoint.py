"""Checkpoint and resume support for long-running scans."""
from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from atlas.logging.setup import get_logger

logger = get_logger(__name__)


class ScanCheckpoint:
    """Manages scan checkpoints for resume capability.

    Saves completed probe names and partial results as JSON.
    On resume, completed probes are skipped.
    """

    def __init__(self, scan_id: str, checkpoint_dir: str = ".atlas/checkpoints") -> None:
        self.scan_id = scan_id
        self.checkpoint_dir = Path(checkpoint_dir)
        self.checkpoint_file = self.checkpoint_dir / f"{scan_id}.json"
        self._data: dict[str, Any] = {
            "scan_id": scan_id,
            "started_at": datetime.now(UTC).isoformat(),
            "completed_probes": [],
            "failed_probes": [],
            "partial_results": {},
        }

        # Load existing checkpoint if resuming
        if self.checkpoint_file.exists():
            self._load()

    def _load(self) -> None:
        """Load checkpoint from disk."""
        try:
            with open(self.checkpoint_file) as f:
                self._data = json.load(f)
            logger.info("checkpoint_loaded", scan_id=self.scan_id,
                       completed=len(self._data.get("completed_probes", [])))
        except Exception as e:
            logger.warning("checkpoint_load_failed", error=str(e))

    def save(self) -> None:
        """Save checkpoint to disk."""
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        self._data["updated_at"] = datetime.now(UTC).isoformat()

        with open(self.checkpoint_file, "w") as f:
            json.dump(self._data, f, indent=2, default=str)

        logger.debug("checkpoint_saved", scan_id=self.scan_id)

    def add_completed_probe(self, probe_name: str, result: dict[str, Any] | None = None) -> None:
        """Mark a probe as completed and optionally store its result."""
        if probe_name not in self._data["completed_probes"]:
            self._data["completed_probes"].append(probe_name)
        if result:
            self._data["partial_results"][probe_name] = result
        self.save()

    def add_failed_probe(self, probe_name: str, error: str) -> None:
        """Record a probe failure."""
        self._data["failed_probes"].append({
            "probe": probe_name,
            "error": error,
            "timestamp": datetime.now(UTC).isoformat(),
        })
        self.save()

    def is_completed(self, probe_name: str) -> bool:
        """Check if a probe has already been completed."""
        return probe_name in self._data.get("completed_probes", [])

    @property
    def completed_probes(self) -> list[str]:
        return self._data.get("completed_probes", [])

    @property
    def partial_results(self) -> dict[str, Any]:
        return self._data.get("partial_results", {})

    def cleanup(self) -> None:
        """Remove checkpoint file after successful scan completion."""
        if self.checkpoint_file.exists():
            self.checkpoint_file.unlink()
            logger.info("checkpoint_cleaned", scan_id=self.scan_id)
