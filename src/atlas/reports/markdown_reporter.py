"""Markdown report generator."""
from __future__ import annotations

from pathlib import Path

from atlas.core.models import ScanResult
from atlas.plugins.registry import register


@register("reporters", name="markdown")
class MarkdownReporter:
    """Generates Markdown report from scan results."""

    name = "markdown"
    format = "markdown"

    async def generate(self, result: ScanResult, output_path: str) -> str:
        """Write scan result as Markdown report."""
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        lines = []
        score = result.security_score

        # Header
        lines.append(f"# ATLAS Security Scan Report")
        lines.append("")
        lines.append(f"**Model:** {result.model_name}")
        lines.append(f"**Profile:** {result.profile}")
        lines.append(f"**Scan ID:** {result.scan_id}")
        lines.append(f"**Date:** {result.started_at}")
        if result.duration_ms:
            lines.append(f"**Duration:** {result.duration_ms/1000:.1f}s")
        lines.append("")

        # Security Score
        lines.append("## Security Score")
        lines.append("")
        lines.append(f"| Metric | Value |")
        lines.append(f"|--------|-------|")
        lines.append(f"| Overall Score | **{score.overall_score:.1f}/100** |")
        lines.append(f"| Risk Level | {score.risk_level.value.upper()} |")
        lines.append(f"| Compliance Score | {score.compliance_score:.1f}/100 |")
        lines.append(f"| Failure Rate | {score.weighted_failure_rate:.1%} |")
        lines.append("")

        # Vulnerabilities by severity
        vuln = score.vulnerabilities_by_severity
        lines.append("### Vulnerabilities by Severity")
        lines.append("")
        lines.append("| Severity | Count |")
        lines.append("|----------|-------|")
        for sev, count in vuln.items():
            lines.append(f"| {sev.capitalize()} | {count} |")
        lines.append("")

        # Category scores
        if score.category_scores:
            lines.append("### Category Scores")
            lines.append("")
            lines.append("| Category | Score |")
            lines.append("|----------|-------|")
            for cat, cat_score in sorted(score.category_scores.items()):
                lines.append(f"| {cat} | {cat_score:.1f}/100 |")
            lines.append("")

        # Probe Results
        lines.append("## Probe Results")
        lines.append("")
        lines.append("| Probe | Total | Passed | Failed | Pass Rate |")
        lines.append("|-------|-------|--------|--------|-----------|")
        for name, pr in result.probe_results.items():
            lines.append(f"| {name} | {pr.total_attempts} | {pr.passed} | {pr.failed} | {pr.pass_rate:.1f}% |")
        lines.append("")

        # Compliance Assessment
        ca = result.compliance_assessment
        if ca.article_details:
            lines.append("## EU AI Act Compliance")
            lines.append("")
            lines.append(f"**Overall Status:** {ca.overall_status.value}")
            lines.append(f"**Articles Assessed:** {ca.articles_assessed}")
            lines.append(f"**Passed:** {ca.articles_passed} | **Failed:** {ca.articles_failed}")
            lines.append("")
            lines.append("| Article | Title | Status | Findings | Critical |")
            lines.append("|---------|-------|--------|----------|----------|")
            for a in ca.article_details:
                lines.append(f"| {a.article_id} | {a.title} | {a.status.value} | {a.findings_count} | {a.critical_findings} |")
            lines.append("")

        # Recommendations
        if result.recommendations:
            lines.append("## Recommendations")
            lines.append("")
            for rec in result.recommendations:
                lines.append(f"- {rec}")
            lines.append("")

        # Findings detail (first 50)
        findings = [f for f in result.findings if not f.passed]
        if findings:
            lines.append("## Failed Findings (Details)")
            lines.append("")
            for i, f in enumerate(findings[:50], 1):
                lines.append(f"### {i}. [{f.severity.value.upper()}] {f.category.value}")
                lines.append(f"**Probe:** {f.attempt.probe_name}")
                lines.append(f"**Prompt:** `{f.attempt.prompt[:200]}...`" if len(f.attempt.prompt) > 200 else f"**Prompt:** `{f.attempt.prompt}`")
                if f.attempt.response:
                    resp_preview = f.attempt.response[:300]
                    lines.append(f"**Response:** `{resp_preview}...`" if len(f.attempt.response) > 300 else f"**Response:** `{f.attempt.response}`")
                if f.compliance_articles:
                    lines.append(f"**EU AI Act:** {', '.join(f.compliance_articles)}")
                if f.owasp_categories:
                    lines.append(f"**OWASP:** {', '.join(f.owasp_categories)}")
                lines.append("")

        # Footer
        lines.append("---")
        lines.append("*Generated by ATLAS (Automated Testing for LLM Assurance & Security)*")

        with open(path, "w") as f:
            f.write("\n".join(lines))

        return str(path)
