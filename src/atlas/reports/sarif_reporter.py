"""SARIF 2.1.0 report generator for GitHub Code Scanning integration."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import atlas
from atlas.core.enums import Severity, VulnerabilityCategory
from atlas.core.models import Finding, ScanResult
from atlas.plugins.registry import register

# SARIF 2.1.0 schema URI
_SARIF_SCHEMA = (
    "https://docs.oasis-open.org/sarif/sarif/v2.1.0/errata01/os/"
    "schemas/sarif-schema-2.1.0.json"
)

# Mapping from ATLAS severity to SARIF level.
# SARIF defines three levels: "error", "warning", and "note".
_SEVERITY_TO_SARIF_LEVEL: dict[Severity, str] = {
    Severity.CRITICAL: "error",
    Severity.HIGH: "error",
    Severity.MEDIUM: "warning",
    Severity.LOW: "note",
    Severity.INFO: "note",
}

# Mapping from vulnerability category to a stable ATLAS rule-id prefix.
_CATEGORY_RULE_PREFIX: dict[VulnerabilityCategory, str] = {
    VulnerabilityCategory.PROMPT_INJECTION: "ATLAS-PI",
    VulnerabilityCategory.JAILBREAK: "ATLAS-JB",
    VulnerabilityCategory.DATA_EXTRACTION: "ATLAS-DE",
    VulnerabilityCategory.TOXICITY: "ATLAS-TX",
    VulnerabilityCategory.HALLUCINATION: "ATLAS-HL",
    VulnerabilityCategory.MALWARE: "ATLAS-MW",
    VulnerabilityCategory.WEB_INJECTION: "ATLAS-WI",
    VulnerabilityCategory.ENCODING: "ATLAS-EN",
    VulnerabilityCategory.HARMFUL_CONTENT: "ATLAS-HC",
    VulnerabilityCategory.PII_LEAKAGE: "ATLAS-PII",
    VulnerabilityCategory.BIAS_FAIRNESS: "ATLAS-BF",
    VulnerabilityCategory.EXCESSIVE_AGENCY: "ATLAS-EA",
    VulnerabilityCategory.DENIAL_OF_SERVICE: "ATLAS-DOS",
    VulnerabilityCategory.RAG_POISONING: "ATLAS-RAG",
    VulnerabilityCategory.FUNCTION_CALLING: "ATLAS-FC",
    VulnerabilityCategory.INDIRECT_INJECTION: "ATLAS-II",
    VulnerabilityCategory.LANGUAGE_CROSSOVER: "ATLAS-LC",
    VulnerabilityCategory.ROLE_PLAY: "ATLAS-RP",
    VulnerabilityCategory.CONTEXT_OVERFLOW: "ATLAS-CO",
    VulnerabilityCategory.STEGANOGRAPHIC: "ATLAS-SG",
    VulnerabilityCategory.SOCIAL_ENGINEERING: "ATLAS-SE",
    VulnerabilityCategory.OTHER: "ATLAS-OTH",
}

# Human-readable descriptions for each vulnerability category.
_CATEGORY_DESCRIPTIONS: dict[VulnerabilityCategory, str] = {
    VulnerabilityCategory.PROMPT_INJECTION: (
        "The model is susceptible to prompt injection attacks that override "
        "system instructions."
    ),
    VulnerabilityCategory.JAILBREAK: (
        "The model can be jailbroken to bypass safety guardrails."
    ),
    VulnerabilityCategory.DATA_EXTRACTION: (
        "The model may leak sensitive data such as system prompts or training data."
    ),
    VulnerabilityCategory.TOXICITY: (
        "The model can be induced to generate toxic or harmful content."
    ),
    VulnerabilityCategory.HALLUCINATION: (
        "The model produces fabricated or factually incorrect information."
    ),
    VulnerabilityCategory.MALWARE: (
        "The model can be manipulated into generating malware or exploit code."
    ),
    VulnerabilityCategory.WEB_INJECTION: (
        "The model outputs may contain web injection payloads (XSS, SSRF, etc.)."
    ),
    VulnerabilityCategory.ENCODING: (
        "The model fails to handle encoded or obfuscated attack payloads."
    ),
    VulnerabilityCategory.HARMFUL_CONTENT: (
        "The model can generate harmful, dangerous, or illegal content."
    ),
    VulnerabilityCategory.PII_LEAKAGE: (
        "The model may leak personally identifiable information."
    ),
    VulnerabilityCategory.BIAS_FAIRNESS: (
        "The model exhibits bias or fairness issues in its outputs."
    ),
    VulnerabilityCategory.EXCESSIVE_AGENCY: (
        "The model takes actions beyond its intended scope or authority."
    ),
    VulnerabilityCategory.DENIAL_OF_SERVICE: (
        "The model is vulnerable to denial-of-service attack patterns."
    ),
    VulnerabilityCategory.RAG_POISONING: (
        "The model's RAG pipeline can be poisoned with malicious content."
    ),
    VulnerabilityCategory.FUNCTION_CALLING: (
        "The model can be tricked into making unsafe function/tool calls."
    ),
    VulnerabilityCategory.INDIRECT_INJECTION: (
        "The model is susceptible to indirect prompt injection via external content."
    ),
    VulnerabilityCategory.LANGUAGE_CROSSOVER: (
        "The model's safety filters can be bypassed using language switching."
    ),
    VulnerabilityCategory.ROLE_PLAY: (
        "The model can be manipulated through role-playing scenarios to bypass safety."
    ),
    VulnerabilityCategory.CONTEXT_OVERFLOW: (
        "The model's context window can be exploited to override instructions."
    ),
    VulnerabilityCategory.STEGANOGRAPHIC: (
        "The model fails to detect steganographic or hidden attack payloads."
    ),
    VulnerabilityCategory.SOCIAL_ENGINEERING: (
        "The model can be socially engineered to bypass safety measures."
    ),
    VulnerabilityCategory.OTHER: (
        "A security finding that does not fall into a specific category."
    ),
}


@register("reporters", name="sarif")
class SARIFReporter:
    """Generates SARIF 2.1.0 reports for GitHub Code Scanning and other SARIF consumers.

    The Static Analysis Results Interchange Format (SARIF) is an OASIS standard
    for the output of static analysis tools.  GitHub Code Scanning natively
    ingests SARIF files, making this reporter the primary integration point for
    GitHub Actions CI/CD pipelines.

    Reference: https://docs.oasis-open.org/sarif/sarif/v2.1.0/
    """

    name = "sarif"
    format = "json"

    async def generate(self, result: ScanResult, output_path: str) -> str:
        """Generate a SARIF 2.1.0 JSON file from scan results.

        Args:
            result: The completed scan result containing findings.
            output_path: Filesystem path where the SARIF file will be written.

        Returns:
            The absolute path to the written file.
        """
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        sarif = self._build_sarif(result)

        with open(path, "w", encoding="utf-8") as fh:
            json.dump(sarif, fh, indent=2, default=str)

        return str(path)

    # ------------------------------------------------------------------
    # Internal builders
    # ------------------------------------------------------------------

    def _build_sarif(self, result: ScanResult) -> dict[str, Any]:
        """Build the top-level SARIF log object."""
        rules = self._build_rules(result)
        rule_index = {r["id"]: idx for idx, r in enumerate(rules)}
        results = self._build_results(result, rule_index)

        run: dict[str, Any] = {
            "tool": {
                "driver": {
                    "name": "ATLAS",
                    "fullName": "ATLAS - Automated Testing for LLM Application Security",
                    "version": atlas.__version__,
                    "semanticVersion": atlas.__version__,
                    "informationUri": "https://github.com/atlas-security/atlas",
                    "rules": rules,
                },
            },
            "results": results,
            "invocations": [self._build_invocation(result)],
        }

        # Attach summary properties via run-level custom properties.
        run["properties"] = self._build_run_properties(result)

        return {
            "$schema": _SARIF_SCHEMA,
            "version": "2.1.0",
            "runs": [run],
        }

    def _build_rules(self, result: ScanResult) -> list[dict[str, Any]]:
        """Build the SARIF ``reportingDescriptor`` (rule) objects.

        One rule is emitted per unique (category, severity) pair that appears
        in the findings, so that GitHub can group results meaningfully.
        """
        seen: dict[str, dict[str, Any]] = {}

        for finding in result.findings:
            if finding.passed:
                continue

            rule_id = self._rule_id_for(finding)
            if rule_id in seen:
                continue

            category = finding.category
            short_desc = f"LLM {category.value.replace('_', ' ').title()} vulnerability"
            full_desc = _CATEGORY_DESCRIPTIONS.get(category, short_desc)

            help_lines = [full_desc, ""]
            if finding.remediation:
                help_lines.append(f"**Remediation:** {finding.remediation}")
            if finding.owasp_categories:
                help_lines.append(
                    f"**OWASP LLM Top 10:** {', '.join(finding.owasp_categories)}"
                )
            if finding.compliance_articles:
                help_lines.append(
                    f"**EU AI Act:** {', '.join(finding.compliance_articles)}"
                )

            rule: dict[str, Any] = {
                "id": rule_id,
                "name": category.value,
                "shortDescription": {"text": short_desc},
                "fullDescription": {"text": full_desc},
                "helpUri": "https://github.com/atlas-security/atlas",
                "help": {
                    "text": "\n".join(help_lines),
                    "markdown": "\n\n".join(help_lines),
                },
                "defaultConfiguration": {
                    "level": _SEVERITY_TO_SARIF_LEVEL.get(
                        finding.severity, "warning"
                    ),
                },
                "properties": {
                    "tags": [
                        "security",
                        f"severity/{finding.severity.value}",
                        f"category/{category.value}",
                        *[f"owasp/{o}" for o in finding.owasp_categories],
                        *[f"eu-ai-act/{a}" for a in finding.compliance_articles],
                    ],
                },
            }
            seen[rule_id] = rule

        return list(seen.values())

    def _build_results(
        self,
        result: ScanResult,
        rule_index: dict[str, int],
    ) -> list[dict[str, Any]]:
        """Build the SARIF ``result`` objects from scan findings."""
        sarif_results: list[dict[str, Any]] = []

        for finding in result.findings:
            if finding.passed:
                # Only report failures in SARIF -- passing probes are not
                # "results" in the static-analysis sense.
                continue

            rule_id = self._rule_id_for(finding)
            level = _SEVERITY_TO_SARIF_LEVEL.get(finding.severity, "warning")

            # Build the message body with relevant details.
            message_parts = [
                finding.description or self._default_description(finding),
            ]
            if finding.attempt.prompt:
                prompt_preview = finding.attempt.prompt[:500]
                if len(finding.attempt.prompt) > 500:
                    prompt_preview += "..."
                message_parts.append(f"Prompt: {prompt_preview}")
            if finding.attempt.response:
                response_preview = finding.attempt.response[:500]
                if len(finding.attempt.response) > 500:
                    response_preview += "..."
                message_parts.append(f"Response: {response_preview}")

            # Collect detector evidence.
            evidence_parts: list[str] = []
            for dr in finding.detector_results:
                status = "passed" if dr.passed else "FAILED"
                evidence_parts.append(
                    f"[{dr.detector_name}] {status} "
                    f"(score={dr.score:.2f}, confidence={dr.confidence:.2f})"
                )
                if dr.evidence:
                    evidence_parts.append(f"  Evidence: {dr.evidence}")

            sarif_result: dict[str, Any] = {
                "ruleId": rule_id,
                "ruleIndex": rule_index.get(rule_id, 0),
                "level": level,
                "message": {
                    "text": "\n".join(message_parts),
                },
                # Use a logical location that identifies the model and probe,
                # since LLM security scans do not target source files.
                "locations": [
                    {
                        "logicalLocations": [
                            {
                                "fullyQualifiedName": (
                                    f"{result.model_name}/"
                                    f"{finding.attempt.probe_name}"
                                ),
                                "kind": "module",
                                "name": finding.attempt.probe_name,
                            }
                        ],
                    }
                ],
                "properties": {
                    "findingId": finding.id,
                    "severity": finding.severity.value,
                    "category": finding.category.value,
                    "probeName": finding.attempt.probe_name,
                    "complianceArticles": finding.compliance_articles,
                    "owaspCategories": finding.owasp_categories,
                    "detectorEvidence": evidence_parts,
                },
            }

            # Attach remediation as a fix suggestion if available.
            if finding.remediation:
                sarif_result["fixes"] = [
                    {
                        "description": {
                            "text": finding.remediation,
                        },
                    }
                ]

            sarif_results.append(sarif_result)

        return sarif_results

    def _build_invocation(self, result: ScanResult) -> dict[str, Any]:
        """Build the SARIF ``invocation`` object with execution metadata."""
        failed_count = sum(1 for f in result.findings if not f.passed)
        invocation: dict[str, Any] = {
            "executionSuccessful": True,
            "startTimeUtc": result.started_at.isoformat(),
            "properties": {
                "scanId": result.scan_id,
                "modelName": result.model_name,
                "provider": result.provider,
                "profile": result.profile,
                "durationMs": result.duration_ms,
                "totalFindings": len(result.findings),
                "failedFindings": failed_count,
            },
        }
        if result.completed_at:
            invocation["endTimeUtc"] = result.completed_at.isoformat()
        return invocation

    def _build_run_properties(self, result: ScanResult) -> dict[str, Any]:
        """Build custom run-level properties with score and compliance summary."""
        score = result.security_score
        ca = result.compliance_assessment
        return {
            "securityScore": score.overall_score,
            "riskLevel": score.risk_level.value,
            "complianceScore": score.compliance_score,
            "complianceStatus": ca.overall_status.value,
            "vulnerabilitiesBySeverity": score.vulnerabilities_by_severity,
            "probeCount": len(result.probe_results),
            "recommendations": result.recommendations,
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _rule_id_for(finding: Finding) -> str:
        """Derive a stable SARIF rule ID from a finding's category and severity."""
        prefix = _CATEGORY_RULE_PREFIX.get(finding.category, "ATLAS-OTH")
        return f"{prefix}/{finding.severity.value}"

    @staticmethod
    def _default_description(finding: Finding) -> str:
        """Produce a fallback description when the finding has none."""
        return (
            f"LLM security finding in category '{finding.category.value}' "
            f"(severity: {finding.severity.value}) detected by probe "
            f"'{finding.attempt.probe_name}'."
        )
