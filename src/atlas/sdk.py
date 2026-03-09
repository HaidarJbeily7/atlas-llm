"""ATLAS SDK - Clean programmatic API for LLM security scanning.

Usage:
    import atlas

    # Async
    result = await atlas.scan(model="openai/gpt-4o", probes=["agent_harm"])

    # Sync
    result = atlas.scan_sync(model="openai/gpt-4o", probes=["agent_harm"])

    print(result.summary())
    print(result.score)
    result.save("report.json")
"""
from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

from atlas.config.models import AtlasConfig, ProviderConfig, ScanConfig
from atlas.core.models import ScanResult


class ScanReport:
    """User-friendly wrapper around ScanResult with convenience methods."""

    def __init__(self, result: ScanResult) -> None:
        self.result = result

    @property
    def score(self) -> float:
        """Overall security score (0-100)."""
        return self.result.security_score.overall_score

    @property
    def risk_level(self) -> str:
        """Risk level string (e.g. 'high', 'critical')."""
        return self.result.security_score.risk_level.value

    @property
    def pass_rate(self) -> float:
        """Overall pass rate across all probes (0-100)."""
        if not self.result.findings:
            return 100.0
        passed = sum(1 for f in self.result.findings if f.passed)
        return round((passed / len(self.result.findings)) * 100, 2)

    @property
    def total_findings(self) -> int:
        """Total number of findings."""
        return len(self.result.findings)

    @property
    def failed_findings(self) -> int:
        """Number of failed findings."""
        return sum(1 for f in self.result.findings if not f.passed)

    def summary(self) -> str:
        """Generate a rich-formatted text summary of the scan results."""
        lines = [
            "ATLAS Security Scan Report",
            "=" * 50,
            f"Model:        {self.result.model_name}",
            f"Score:        {self.score:.1f}/100",
            f"Risk Level:   {self.risk_level.upper()}",
            f"Pass Rate:    {self.pass_rate:.1f}%",
            f"Findings:     {self.total_findings} total, {self.failed_findings} failed",
            f"Duration:     {self.result.duration_ms:.0f}ms",
            "",
        ]

        # Probe results breakdown
        if self.result.probe_results:
            lines.append("Probe Results:")
            lines.append(f"{'-' * 50}")
            for name, pr in self.result.probe_results.items():
                status = "PASS" if pr.failed == 0 else "FAIL"
                lines.append(
                    f"  {name:<25} {status:<6} "
                    f"({pr.passed}/{pr.total_attempts} passed, {pr.pass_rate:.1f}%)"
                )
            lines.append("")

        # Category scores
        if self.result.security_score.category_scores:
            lines.append("Category Scores:")
            lines.append(f"{'-' * 50}")
            for cat, cat_score in self.result.security_score.category_scores.items():
                lines.append(f"  {cat:<25} {cat_score:.1f}/100")
            lines.append("")

        # Recommendations
        if self.result.recommendations:
            lines.append("Recommendations:")
            lines.append(f"{'-' * 50}")
            for rec in self.result.recommendations:
                lines.append(f"  - {rec}")

        return "\n".join(lines)

    def save(self, path: str) -> None:
        """Save report to file. Format auto-detected from extension.

        Supports: .json, .html, .md
        """
        p = Path(path)
        suffix = p.suffix.lower()

        if suffix == ".json":
            p.write_text(
                json.dumps(self.to_dict(), indent=2, default=str),
                encoding="utf-8",
            )
        elif suffix == ".html":
            self._save_html(p)
        elif suffix in (".md", ".markdown"):
            p.write_text(self.summary(), encoding="utf-8")
        else:
            # Default to JSON
            p.write_text(
                json.dumps(self.to_dict(), indent=2, default=str),
                encoding="utf-8",
            )

    def to_dict(self) -> dict[str, Any]:
        """Convert to a JSON-serializable dictionary."""
        return self.result.model_dump(mode="json")

    def findings_by_category(self) -> dict[str, list[dict[str, Any]]]:
        """Group findings by vulnerability category."""
        groups: dict[str, list[dict[str, Any]]] = {}
        for f in self.result.findings:
            cat = f.category.value
            groups.setdefault(cat, []).append(f.model_dump(mode="json"))
        return groups

    def findings_by_severity(self) -> dict[str, list[dict[str, Any]]]:
        """Group findings by severity level."""
        groups: dict[str, list[dict[str, Any]]] = {}
        for f in self.result.findings:
            sev = f.severity.value
            groups.setdefault(sev, []).append(f.model_dump(mode="json"))
        return groups

    def _save_html(self, path: Path) -> None:
        """Save a simple HTML report."""
        html = f"""<!DOCTYPE html>
<html><head><title>ATLAS Report - {self.result.model_name}</title>
<style>
body {{ font-family: sans-serif; margin: 2rem; }}
table {{ border-collapse: collapse; width: 100%; }}
th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
th {{ background: #f4f4f4; }}
.pass {{ color: green; }} .fail {{ color: red; }}
</style></head><body>
<h1>ATLAS Security Scan Report</h1>
<p><b>Model:</b> {self.result.model_name} | <b>Score:</b> {self.score:.1f}/100 | <b>Risk:</b> {self.risk_level}</p>
<h2>Probe Results</h2>
<table><tr><th>Probe</th><th>Status</th><th>Pass Rate</th><th>Passed</th><th>Failed</th></tr>"""
        for name, pr in self.result.probe_results.items():
            status_cls = "pass" if pr.failed == 0 else "fail"
            status_txt = "PASS" if pr.failed == 0 else "FAIL"
            html += (
                f'<tr><td>{name}</td><td class="{status_cls}">{status_txt}</td>'
                f"<td>{pr.pass_rate:.1f}%</td><td>{pr.passed}</td><td>{pr.failed}</td></tr>"
            )
        html += "</table></body></html>"
        path.write_text(html, encoding="utf-8")

    def __repr__(self) -> str:
        return (
            f"ScanReport(model={self.result.model_name!r}, "
            f"score={self.score:.1f}, risk={self.risk_level!r}, "
            f"findings={self.total_findings})"
        )


async def scan(
    model: str,
    probes: list[str] | None = None,
    detectors: list[str] | None = None,
    profile: str | None = None,
    api_key: str | None = None,
    concurrency: int = 10,
    temperature: float = 0.0,
    timeout: int = 30,
    config: AtlasConfig | None = None,
) -> ScanReport:
    """Run an ATLAS security scan.

    Args:
        model: LiteLLM model string (e.g. "openai/gpt-4o", "anthropic/claude-3-5-sonnet").
        probes: List of probe names to run. If None, uses profile defaults.
        detectors: List of detector names. If None, uses probe defaults.
        profile: Scan profile name (e.g. "quick", "standard", "comprehensive").
        api_key: API key for the LLM provider.
        concurrency: Max concurrent requests to the LLM.
        temperature: LLM temperature setting.
        timeout: Per-request timeout in seconds.
        config: Full AtlasConfig override. If provided, other params are ignored.

    Returns:
        ScanReport with results and convenience methods.

    Example:
        >>> result = await atlas.scan(model="openai/gpt-4o", probes=["agent_harm"])
        >>> print(result.summary())
    """
    from atlas.engine.runner import ScanRunner  # noqa: PLC0415

    if config is None:
        config = AtlasConfig(
            provider=ProviderConfig(
                model=model,
                api_key=api_key,
                timeout=timeout,
                temperature=temperature,
            ),
            scan=ScanConfig(concurrency=concurrency),
        )

    runner = ScanRunner(config)
    result = await runner.run(
        profile=profile,
        probe_names=probes,
        detector_names=detectors,
    )
    return ScanReport(result)


def scan_sync(
    model: str,
    probes: list[str] | None = None,
    detectors: list[str] | None = None,
    profile: str | None = None,
    api_key: str | None = None,
    concurrency: int = 10,
    temperature: float = 0.0,
    timeout: int = 30,
    config: AtlasConfig | None = None,
) -> ScanReport:
    """Synchronous wrapper around scan().

    Same parameters as scan(). Runs the async scan in a new event loop.

    Example:
        >>> result = atlas.scan_sync(model="openai/gpt-4o", probes=["agent_harm"])
        >>> print(result.score)
    """
    return asyncio.run(
        scan(
            model=model,
            probes=probes,
            detectors=detectors,
            profile=profile,
            api_key=api_key,
            concurrency=concurrency,
            temperature=temperature,
            timeout=timeout,
            config=config,
        )
    )
