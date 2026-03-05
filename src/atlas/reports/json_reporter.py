"""JSON report generator."""
from __future__ import annotations

import json
from pathlib import Path

from atlas.core.models import ScanResult
from atlas.plugins.registry import register


@register("reporters", name="json")
class JSONReporter:
    """Generates JSON report from scan results."""

    name = "json"
    format = "json"

    async def generate(self, result: ScanResult, output_path: str) -> str:
        """Write scan result as formatted JSON."""
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        data = result.model_dump(mode="json")
        data["_meta"] = {
            "format": "atlas-scan-result",
            "version": "1.0",
        }

        with open(path, "w") as f:
            json.dump(data, f, indent=2, default=str)

        return str(path)
