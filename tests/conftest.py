"""Shared test fixtures for ATLAS."""
from __future__ import annotations

import pytest

from atlas.core.enums import Severity, VulnerabilityCategory
from atlas.core.models import Attempt, DetectorResult, Finding, ProbeResult, ScanResult, SecurityScore
from atlas.datasets.manager import DatasetManager


@pytest.fixture
def dataset_manager(tmp_path):
    """Create a DatasetManager with a temporary data directory."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()

    # Create some test data files
    import json

    # Test JSON dataset
    (data_dir / "test.json").write_text(json.dumps(["prompt1", "prompt2", "prompt3"]))

    # Test TXT dataset
    (data_dir / "test.txt").write_text("line1\nline2\nline3\n")

    # Test JSONL dataset
    (data_dir / "test.jsonl").write_text('{"prompt": "p1"}\n{"prompt": "p2"}\n')

    # Test subdirectory
    sub = data_dir / "subdir"
    sub.mkdir()
    (sub / "nested.json").write_text(json.dumps({"key": "value"}))

    return DatasetManager(data_dir=data_dir)


@pytest.fixture
def sample_attempt():
    """Create a sample Attempt."""
    return Attempt(
        probe_name="test_probe",
        prompt="Test prompt",
        response="Test response",
        tags=["test"],
    )


@pytest.fixture
def sample_finding(sample_attempt):
    """Create a sample Finding."""
    return Finding(
        attempt=sample_attempt,
        detector_results=[
            DetectorResult(
                detector_name="keyword",
                passed=True,
                score=0.9,
                confidence=0.8,
            ),
        ],
        severity=Severity.MEDIUM,
        category=VulnerabilityCategory.PROMPT_INJECTION,
        passed=True,
        compliance_articles=["article-15-5"],
        owasp_categories=["LLM01"],
    )


@pytest.fixture
def sample_findings():
    """Create a list of varied findings for testing evaluators."""
    findings = []
    categories = [
        (VulnerabilityCategory.PROMPT_INJECTION, Severity.CRITICAL, False),
        (VulnerabilityCategory.PROMPT_INJECTION, Severity.HIGH, False),
        (VulnerabilityCategory.PROMPT_INJECTION, Severity.LOW, True),
        (VulnerabilityCategory.JAILBREAK, Severity.HIGH, False),
        (VulnerabilityCategory.JAILBREAK, Severity.LOW, True),
        (VulnerabilityCategory.JAILBREAK, Severity.LOW, True),
        (VulnerabilityCategory.TOXICITY, Severity.MEDIUM, False),
        (VulnerabilityCategory.TOXICITY, Severity.LOW, True),
        (VulnerabilityCategory.HALLUCINATION, Severity.MEDIUM, False),
        (VulnerabilityCategory.HALLUCINATION, Severity.LOW, True),
    ]
    for cat, sev, passed in categories:
        attempt = Attempt(
            probe_name=cat.value,
            prompt=f"Test prompt for {cat.value}",
            response=f"Test response {'safe' if passed else 'unsafe'}",
        )
        findings.append(Finding(
            attempt=attempt,
            severity=sev,
            category=cat,
            passed=passed,
            compliance_articles=["article-15-5"] if "injection" in cat.value or "jailbreak" in cat.value else ["article-9"],
        ))
    return findings
