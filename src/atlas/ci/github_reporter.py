"""GitHub Pull Request comment formatter for ATLAS scan results."""
from __future__ import annotations

from atlas.core.enums import ComplianceStatus, RiskLevel, Severity
from atlas.core.models import Finding, ScanResult


# Emoji mappings for visual indicators in markdown
_RISK_BADGES: dict[RiskLevel, str] = {
    RiskLevel.CRITICAL: "🔴 Critical",
    RiskLevel.HIGH: "🟠 High",
    RiskLevel.MEDIUM: "🟡 Medium",
    RiskLevel.LOW: "🟢 Low",
    RiskLevel.MINIMAL: "🟢 Minimal",
}

_SEVERITY_ICONS: dict[Severity, str] = {
    Severity.CRITICAL: "🔴",
    Severity.HIGH: "🟠",
    Severity.MEDIUM: "🟡",
    Severity.LOW: "🔵",
    Severity.INFO: "⚪",
}

_COMPLIANCE_ICONS: dict[ComplianceStatus, str] = {
    ComplianceStatus.COMPLIANT: "✅ Compliant",
    ComplianceStatus.NON_COMPLIANT: "❌ Non-Compliant",
    ComplianceStatus.PARTIAL: "⚠️ Partial",
    ComplianceStatus.NOT_ASSESSED: "➖ Not Assessed",
}

_MAX_FAILED_FINDINGS = 10
_MAX_PROMPT_LENGTH = 200
_MAX_RESPONSE_LENGTH = 300


class GitHubPRReporter:
    """Format ATLAS scan results as GitHub PR comments.

    Generates a comprehensive Markdown comment containing:
    - Summary table (score, risk level, pass rate)
    - Probe results breakdown
    - Top failed findings with evidence
    - EU AI Act compliance status
    - Expandable details section with vulnerability breakdown
    """

    def format_comment(self, result: ScanResult) -> str:
        """Format a complete GitHub PR comment from scan results.

        Args:
            result: The completed scan result to format.

        Returns:
            Markdown-formatted string suitable for posting as a GitHub
            PR comment via the GitHub API.
        """
        sections = [
            self._header(),
            self._summary_table(result),
            self._probe_results_table(result),
            self._top_failed_findings(result),
            self._compliance_section(result),
            self._details_section(result),
            self._footer(result),
        ]
        return "\n\n".join(section for section in sections if section)

    # ------------------------------------------------------------------
    # Private section builders
    # ------------------------------------------------------------------

    def _header(self) -> str:
        """Render the comment header."""
        return "## 🛡️ ATLAS Security Scan Results"

    def _summary_table(self, result: ScanResult) -> str:
        """Render the summary metrics table."""
        score = result.security_score
        risk_badge = _RISK_BADGES.get(score.risk_level, str(score.risk_level.value))

        total_probes = len(result.probe_results)
        total_findings = len(result.findings)
        failed_findings = sum(1 for f in result.findings if not f.passed)

        # Overall pass rate across all probes
        if result.probe_results:
            avg_pass_rate = sum(
                pr.pass_rate for pr in result.probe_results.values()
            ) / len(result.probe_results)
        else:
            avg_pass_rate = 100.0

        lines = [
            "### Summary",
            "",
            "| Metric | Value |",
            "|--------|-------|",
            f"| **Model** | `{result.model_name}` |",
            f"| **Security Score** | **{score.overall_score:.1f}**/100 |",
            f"| **Risk Level** | {risk_badge} |",
            f"| **Pass Rate** | {avg_pass_rate:.1f}% |",
            f"| **Probes Run** | {total_probes} |",
            f"| **Total Findings** | {total_findings} |",
            f"| **Failed Findings** | {failed_findings} |",
        ]
        return "\n".join(lines)

    def _probe_results_table(self, result: ScanResult) -> str:
        """Render the per-probe results table."""
        if not result.probe_results:
            return ""

        lines = [
            "### Probe Results",
            "",
            "| Probe | Total | Passed | Failed | Pass Rate | Status |",
            "|-------|------:|-------:|-------:|----------:|--------|",
        ]

        # Sort probes by pass rate (worst first)
        sorted_probes = sorted(
            result.probe_results.values(),
            key=lambda p: p.pass_rate,
        )

        for pr in sorted_probes:
            status = "✅" if pr.pass_rate >= 80.0 else ("⚠️" if pr.pass_rate >= 50.0 else "❌")
            lines.append(
                f"| `{pr.probe_name}` "
                f"| {pr.total_attempts} "
                f"| {pr.passed} "
                f"| {pr.failed} "
                f"| {pr.pass_rate:.1f}% "
                f"| {status} |"
            )

        return "\n".join(lines)

    def _top_failed_findings(self, result: ScanResult) -> str:
        """Render the top N failed findings with truncated evidence."""
        failed = [f for f in result.findings if not f.passed]
        if not failed:
            return "### Top Findings\n\n> No failed findings detected. All probes passed."

        # Sort by severity (critical first)
        severity_order = {
            Severity.CRITICAL: 0,
            Severity.HIGH: 1,
            Severity.MEDIUM: 2,
            Severity.LOW: 3,
            Severity.INFO: 4,
        }
        failed.sort(key=lambda f: severity_order.get(f.severity, 5))

        top = failed[:_MAX_FAILED_FINDINGS]

        lines = [
            f"### Top Failed Findings ({len(top)} of {len(failed)})",
            "",
        ]

        for i, finding in enumerate(top, start=1):
            icon = _SEVERITY_ICONS.get(finding.severity, "⚪")
            prompt_preview = self._truncate(
                finding.attempt.prompt, _MAX_PROMPT_LENGTH
            )
            response_preview = self._truncate(
                finding.attempt.response, _MAX_RESPONSE_LENGTH
            )

            lines.append(
                f"**{i}. {icon} [{finding.severity.value.upper()}] "
                f"{finding.category.value}**"
            )
            lines.append("")
            lines.append(f"> **Prompt:** {prompt_preview}")
            lines.append(f"> **Response:** {response_preview}")
            if finding.remediation:
                lines.append(f"> **Remediation:** {finding.remediation}")
            lines.append("")

        return "\n".join(lines)

    def _compliance_section(self, result: ScanResult) -> str:
        """Render the EU AI Act compliance status section."""
        ca = result.compliance_assessment
        status_text = _COMPLIANCE_ICONS.get(ca.overall_status, str(ca.overall_status.value))

        lines = [
            "### EU AI Act Compliance",
            "",
            "| Metric | Value |",
            "|--------|-------|",
            f"| **Overall Status** | {status_text} |",
            f"| **Articles Assessed** | {ca.articles_assessed} |",
            f"| **Articles Passed** | {ca.articles_passed} |",
            f"| **Articles Failed** | {ca.articles_failed} |",
        ]

        if ca.high_risk_areas:
            areas = ", ".join(f"`{a}`" for a in ca.high_risk_areas)
            lines.append(f"| **High-Risk Areas** | {areas} |")

        return "\n".join(lines)

    def _details_section(self, result: ScanResult) -> str:
        """Render expandable details with vulnerability breakdown and recommendations."""
        score = result.security_score

        vuln_lines = []
        for sev_name, count in score.vulnerabilities_by_severity.items():
            if count > 0:
                icon = _SEVERITY_ICONS.get(Severity(sev_name), "⚪")
                vuln_lines.append(f"- {icon} **{sev_name.capitalize()}**: {count}")

        category_lines = []
        for cat_name, cat_score in sorted(
            score.category_scores.items(), key=lambda x: x[1]
        ):
            bar = self._score_bar(cat_score)
            category_lines.append(f"| `{cat_name}` | {cat_score:.1f} | {bar} |")

        rec_lines = []
        for rec in result.recommendations:
            rec_lines.append(f"- {rec}")

        parts = [
            "<details>",
            "<summary><strong>Detailed Breakdown</strong></summary>",
            "",
        ]

        # Vulnerability severity breakdown
        if vuln_lines:
            parts.append("#### Vulnerabilities by Severity")
            parts.append("")
            parts.extend(vuln_lines)
            parts.append("")

        # Category scores
        if category_lines:
            parts.append("#### Category Scores")
            parts.append("")
            parts.append("| Category | Score | |")
            parts.append("|----------|------:|-|")
            parts.extend(category_lines)
            parts.append("")

        # Recommendations
        if rec_lines:
            parts.append("#### Recommendations")
            parts.append("")
            parts.extend(rec_lines)
            parts.append("")

        parts.append("</details>")

        return "\n".join(parts)

    def _footer(self, result: ScanResult) -> str:
        """Render the comment footer."""
        duration_sec = result.duration_ms / 1000 if result.duration_ms else 0
        return (
            "---\n"
            f"*Scan ID: `{result.scan_id}` | "
            f"Profile: `{result.profile}` | "
            f"Duration: {duration_sec:.1f}s | "
            f"Generated by [ATLAS](https://github.com/atlas-llm/atlas)*"
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _truncate(text: str, max_length: int) -> str:
        """Truncate text and append ellipsis if needed."""
        if not text:
            return "*empty*"
        # Replace newlines for inline display
        text = text.replace("\n", " ").strip()
        if len(text) <= max_length:
            return text
        return text[:max_length] + "..."

    @staticmethod
    def _score_bar(score: float, width: int = 10) -> str:
        """Render a simple text-based progress bar."""
        filled = round(score / 100 * width)
        empty = width - filled
        return f"{'█' * filled}{'░' * empty}"
