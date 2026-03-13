"""JUnit XML report generator for Jenkins, GitLab CI, and other CI/CD systems."""
from __future__ import annotations

from pathlib import Path
from xml.etree.ElementTree import Element, SubElement, ElementTree, indent

from atlas.core.models import Finding, ProbeResult, ScanResult
from atlas.plugins.registry import register


def _xml_safe(text: str) -> str:
    """Ensure text is safe for XML content (strip control characters)."""
    # Remove XML-illegal control characters (except tab, newline, carriage return).
    return "".join(
        ch if ch in ("\t", "\n", "\r") or ord(ch) >= 0x20 else "?" for ch in text
    )


@register("reporters", name="junit")
class JUnitReporter:
    """Generates JUnit XML reports compatible with Jenkins, GitLab CI, and GitHub Actions.

    The report follows the standard JUnit XML schema where:
    - Each probe maps to a ``<testsuite>``
    - Each finding within that probe maps to a ``<testcase>``
    - Passed findings produce plain ``<testcase>`` elements (success)
    - Failed findings include a ``<failure>`` child with evidence details
    - Skipped probes with zero attempts get a ``<skipped>`` marker

    This allows CI/CD systems to display per-probe pass/fail status and
    drill into individual finding details on failure.
    """

    name = "junit"
    format = "xml"

    async def generate(self, result: ScanResult, output_path: str) -> str:
        """Generate a JUnit XML file from scan results.

        Args:
            result: The completed scan result containing probe results and findings.
            output_path: Filesystem path where the XML file will be written.

        Returns:
            The absolute path to the written file.
        """
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        root = self._build_testsuites(result)
        tree = ElementTree(root)
        indent(tree, space="  ")

        with open(path, "wb") as fh:
            tree.write(fh, encoding="utf-8", xml_declaration=True)

        return str(path)

    # ------------------------------------------------------------------
    # Internal builders
    # ------------------------------------------------------------------

    def _build_testsuites(self, result: ScanResult) -> Element:
        """Build the top-level ``<testsuites>`` element."""
        total_tests = 0
        total_failures = 0
        total_errors = 0
        total_time = result.duration_ms / 1000.0

        root = Element("testsuites")
        root.set("name", f"ATLAS Security Scan - {result.model_name}")
        root.set("id", result.scan_id)
        root.set("timestamp", result.started_at.isoformat())

        for probe_name, probe_result in result.probe_results.items():
            suite = self._build_testsuite(result, probe_name, probe_result)
            root.append(suite)
            total_tests += int(suite.get("tests", "0"))
            total_failures += int(suite.get("failures", "0"))
            total_errors += int(suite.get("errors", "0"))

        root.set("tests", str(total_tests))
        root.set("failures", str(total_failures))
        root.set("errors", str(total_errors))
        root.set("time", f"{total_time:.3f}")

        return root

    def _build_testsuite(
        self,
        result: ScanResult,
        probe_name: str,
        probe_result: ProbeResult,
    ) -> Element:
        """Build a ``<testsuite>`` element for a single probe."""
        suite = Element("testsuite")
        suite.set("name", probe_name)
        suite.set("tests", str(probe_result.total_attempts))
        suite.set("failures", str(probe_result.failed))
        suite.set("errors", "0")
        suite.set("skipped", "0")
        suite.set("timestamp", result.started_at.isoformat())

        # Estimate per-probe time by distributing total duration proportionally.
        total_attempts = sum(
            pr.total_attempts for pr in result.probe_results.values()
        )
        if total_attempts > 0:
            probe_time = (
                result.duration_ms / 1000.0
                * probe_result.total_attempts
                / total_attempts
            )
        else:
            probe_time = 0.0
        suite.set("time", f"{probe_time:.3f}")

        # Add suite-level properties with probe metadata.
        props = SubElement(suite, "properties")
        self._add_property(props, "category", probe_result.category.value)
        self._add_property(props, "pass_rate", f"{probe_result.pass_rate:.1f}%")
        self._add_property(props, "model", result.model_name)
        self._add_property(props, "provider", result.provider)
        self._add_property(props, "profile", result.profile)
        if probe_result.compliance_articles:
            self._add_property(
                props,
                "compliance_articles",
                ", ".join(probe_result.compliance_articles),
            )

        # Handle edge case: probe declared but never ran.
        if probe_result.total_attempts == 0:
            suite.set("skipped", "1")
            tc = SubElement(suite, "testcase")
            tc.set("name", f"{probe_name} (no attempts)")
            tc.set("classname", f"atlas.probes.{probe_name}")
            tc.set("time", "0.000")
            skipped = SubElement(tc, "skipped")
            skipped.set("message", "Probe produced zero attempts")
            return suite

        # Build a testcase for each finding.
        for finding in probe_result.findings:
            tc = self._build_testcase(probe_name, finding)
            suite.append(tc)

        return suite

    def _build_testcase(self, probe_name: str, finding: Finding) -> Element:
        """Build a ``<testcase>`` element for a single finding.

        Passed findings get a bare ``<testcase>``; failed findings include a
        ``<failure>`` child element with detailed evidence.
        """
        tc = Element("testcase")
        tc.set(
            "name",
            _xml_safe(
                f"[{finding.severity.value.upper()}] "
                f"{finding.category.value} - {finding.id[:8]}"
            ),
        )
        tc.set("classname", f"atlas.probes.{probe_name}")
        tc.set("time", "0.000")

        if not finding.passed:
            failure = SubElement(tc, "failure")
            failure.set(
                "message",
                _xml_safe(
                    finding.description
                    or f"{finding.category.value} vulnerability detected"
                ),
            )
            failure.set("type", finding.severity.value)
            failure.text = _xml_safe(self._build_failure_text(finding))

        # Always attach finding details in system-out for traceability.
        system_out = SubElement(tc, "system-out")
        system_out.text = _xml_safe(self._build_system_out(finding))

        return tc

    # ------------------------------------------------------------------
    # Text formatting helpers
    # ------------------------------------------------------------------

    def _build_failure_text(self, finding: Finding) -> str:
        """Build the full-text body of a ``<failure>`` element."""
        lines: list[str] = []

        lines.append(f"Severity: {finding.severity.value.upper()}")
        lines.append(f"Category: {finding.category.value}")
        lines.append(f"Finding ID: {finding.id}")
        lines.append("")

        # Prompt (truncated for readability in CI logs)
        if finding.attempt.prompt:
            prompt_preview = finding.attempt.prompt[:1000]
            if len(finding.attempt.prompt) > 1000:
                prompt_preview += "... [truncated]"
            lines.append(f"Prompt:\n{prompt_preview}")
            lines.append("")

        # Response (truncated)
        if finding.attempt.response:
            response_preview = finding.attempt.response[:1000]
            if len(finding.attempt.response) > 1000:
                response_preview += "... [truncated]"
            lines.append(f"Response:\n{response_preview}")
            lines.append("")

        # Detector evidence
        if finding.detector_results:
            lines.append("Detector Results:")
            for dr in finding.detector_results:
                status = "PASSED" if dr.passed else "FAILED"
                lines.append(
                    f"  - [{dr.detector_name}] {status} "
                    f"(score={dr.score:.2f}, confidence={dr.confidence:.2f})"
                )
                if dr.evidence:
                    lines.append(f"    Evidence: {dr.evidence}")
            lines.append("")

        # Remediation
        if finding.remediation:
            lines.append(f"Remediation: {finding.remediation}")
            lines.append("")

        # Compliance references
        if finding.compliance_articles:
            lines.append(f"EU AI Act Articles: {', '.join(finding.compliance_articles)}")
        if finding.owasp_categories:
            lines.append(f"OWASP LLM Top 10: {', '.join(finding.owasp_categories)}")

        return "\n".join(lines)

    def _build_system_out(self, finding: Finding) -> str:
        """Build the ``<system-out>`` text with a concise finding summary."""
        lines: list[str] = [
            f"finding_id={finding.id}",
            f"passed={finding.passed}",
            f"severity={finding.severity.value}",
            f"category={finding.category.value}",
            f"probe={finding.attempt.probe_name}",
        ]
        if finding.compliance_articles:
            lines.append(f"compliance={','.join(finding.compliance_articles)}")
        if finding.owasp_categories:
            lines.append(f"owasp={','.join(finding.owasp_categories)}")
        return "\n".join(lines)

    @staticmethod
    def _add_property(parent: Element, name: str, value: str) -> None:
        """Add a ``<property>`` child element."""
        prop = SubElement(parent, "property")
        prop.set("name", name)
        prop.set("value", value)
