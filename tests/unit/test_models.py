"""Tests for core data models."""
from atlas.core.enums import RiskLevel, Severity, VulnerabilityCategory
from atlas.core.models import Attempt, DetectorResult, Finding, ProbeResult, ScanResult, SecurityScore


class TestAttempt:
    def test_create_attempt(self):
        a = Attempt(probe_name="test", prompt="hello")
        assert a.probe_name == "test"
        assert a.prompt == "hello"
        assert a.response == ""
        assert a.id  # UUID generated

    def test_attempt_with_metadata(self):
        a = Attempt(probe_name="test", prompt="hello", metadata={"key": "val"}, tags=["t1"])
        assert a.metadata == {"key": "val"}
        assert a.tags == ["t1"]


class TestDetectorResult:
    def test_create_result(self):
        r = DetectorResult(detector_name="keyword", passed=True, score=0.9)
        assert r.passed is True
        assert r.score == 0.9


class TestFinding:
    def test_create_finding(self, sample_attempt):
        f = Finding(
            attempt=sample_attempt,
            severity=Severity.HIGH,
            category=VulnerabilityCategory.JAILBREAK,
            passed=False,
        )
        assert f.severity == Severity.HIGH
        assert f.passed is False
        assert f.id  # UUID generated


class TestSecurityScore:
    def test_default_score(self):
        s = SecurityScore()
        assert s.overall_score == 0.0
        assert s.risk_level == RiskLevel.HIGH


class TestScanResult:
    def test_create_scan_result(self):
        r = ScanResult(model_name="gpt-4o", provider="openai")
        assert r.model_name == "gpt-4o"
        assert r.scan_id  # UUID generated

    def test_serialization_roundtrip(self, sample_finding):
        r = ScanResult(
            model_name="test",
            provider="test",
            findings=[sample_finding],
        )
        data = r.model_dump(mode="json")
        restored = ScanResult.model_validate(data)
        assert restored.model_name == "test"
        assert len(restored.findings) == 1
