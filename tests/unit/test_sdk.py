"""Tests for ATLAS SDK."""
from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from atlas.config.models import AtlasConfig
from atlas.core.enums import RiskLevel, Severity, VulnerabilityCategory
from atlas.core.models import (
    Attempt,
    DetectorResult,
    Finding,
    ProbeResult,
    ScanResult,
    SecurityScore,
)
from atlas.sdk import ScanReport, scan, scan_sync


def _make_scan_result(
    model: str = "openai/gpt-4o",
    score: float = 75.0,
    risk_level: RiskLevel = RiskLevel.MEDIUM,
) -> ScanResult:
    """Create a ScanResult for testing."""
    attempt_pass = Attempt(probe_name="test", prompt="safe prompt", response="I cannot help")
    attempt_fail = Attempt(probe_name="test", prompt="bad prompt", response="Sure, here's how")

    finding_pass = Finding(
        attempt=attempt_pass,
        detector_results=[DetectorResult(detector_name="keyword", passed=True, score=0.9)],
        severity=Severity.LOW,
        category=VulnerabilityCategory.HARMFUL_CONTENT,
        passed=True,
    )
    finding_fail = Finding(
        attempt=attempt_fail,
        detector_results=[DetectorResult(detector_name="keyword", passed=False, score=0.2)],
        severity=Severity.HIGH,
        category=VulnerabilityCategory.HARMFUL_CONTENT,
        passed=False,
    )

    probe_result = ProbeResult(
        probe_name="test",
        category=VulnerabilityCategory.HARMFUL_CONTENT,
        total_attempts=2,
        passed=1,
        failed=1,
        pass_rate=50.0,
        findings=[finding_pass, finding_fail],
    )

    return ScanResult(
        model_name=model,
        provider="openai",
        probe_results={"test": probe_result},
        findings=[finding_pass, finding_fail],
        security_score=SecurityScore(
            overall_score=score,
            risk_level=risk_level,
            category_scores={"harmful_content": score},
        ),
        duration_ms=1234.5,
    )


class TestScanReport:
    def test_score(self):
        report = ScanReport(_make_scan_result(score=82.5))
        assert report.score == 82.5

    def test_risk_level(self):
        report = ScanReport(_make_scan_result(risk_level=RiskLevel.HIGH))
        assert report.risk_level == "high"

    def test_pass_rate(self):
        report = ScanReport(_make_scan_result())
        assert report.pass_rate == 50.0

    def test_pass_rate_no_findings(self):
        result = ScanResult(model_name="test")
        report = ScanReport(result)
        assert report.pass_rate == 100.0

    def test_total_findings(self):
        report = ScanReport(_make_scan_result())
        assert report.total_findings == 2

    def test_failed_findings(self):
        report = ScanReport(_make_scan_result())
        assert report.failed_findings == 1

    def test_summary_contains_key_info(self):
        report = ScanReport(_make_scan_result())
        summary = report.summary()
        assert "openai/gpt-4o" in summary
        assert "75.0" in summary
        assert "MEDIUM" in summary
        assert "50.0%" in summary

    def test_to_dict(self):
        report = ScanReport(_make_scan_result())
        d = report.to_dict()
        assert d["model_name"] == "openai/gpt-4o"
        assert "findings" in d
        assert "security_score" in d

    def test_findings_by_category(self):
        report = ScanReport(_make_scan_result())
        by_cat = report.findings_by_category()
        assert "harmful_content" in by_cat
        assert len(by_cat["harmful_content"]) == 2

    def test_findings_by_severity(self):
        report = ScanReport(_make_scan_result())
        by_sev = report.findings_by_severity()
        assert "low" in by_sev
        assert "high" in by_sev

    def test_save_json(self, tmp_path):
        report = ScanReport(_make_scan_result())
        path = tmp_path / "report.json"
        report.save(str(path))
        assert path.exists()
        data = json.loads(path.read_text())
        assert data["model_name"] == "openai/gpt-4o"

    def test_save_html(self, tmp_path):
        report = ScanReport(_make_scan_result())
        path = tmp_path / "report.html"
        report.save(str(path))
        assert path.exists()
        content = path.read_text()
        assert "<html>" in content
        assert "openai/gpt-4o" in content

    def test_save_markdown(self, tmp_path):
        report = ScanReport(_make_scan_result())
        path = tmp_path / "report.md"
        report.save(str(path))
        assert path.exists()
        content = path.read_text()
        assert "ATLAS Security Scan Report" in content

    def test_repr(self):
        report = ScanReport(_make_scan_result())
        r = repr(report)
        assert "ScanReport" in r
        assert "openai/gpt-4o" in r
        assert "75.0" in r


class TestScanFunction:
    @pytest.mark.asyncio
    async def test_scan_constructs_config_and_runs(self):
        """scan() should construct AtlasConfig and run ScanRunner."""
        mock_result = _make_scan_result()

        with patch("atlas.engine.runner.ScanRunner") as mock_runner_cls:
            mock_runner_instance = MagicMock()
            mock_runner_instance.run = AsyncMock(return_value=mock_result)
            mock_runner_cls.return_value = mock_runner_instance

            report = await scan(
                model="openai/gpt-4o",
                probes=["agent_harm"],
                detectors=["refusal"],
                concurrency=5,
                temperature=0.1,
                timeout=60,
            )

        assert isinstance(report, ScanReport)
        assert report.score == 75.0

        # Verify config was constructed correctly
        config_arg = mock_runner_cls.call_args[0][0]
        assert isinstance(config_arg, AtlasConfig)
        assert config_arg.provider.model == "openai/gpt-4o"
        assert config_arg.provider.temperature == 0.1
        assert config_arg.provider.timeout == 60
        assert config_arg.scan.concurrency == 5

        # Verify runner.run was called with correct args
        mock_runner_instance.run.assert_awaited_once_with(
            profile=None,
            probe_names=["agent_harm"],
            detector_names=["refusal"],
        )

    @pytest.mark.asyncio
    async def test_scan_with_custom_config(self):
        """scan() should use provided AtlasConfig directly."""
        mock_result = _make_scan_result()
        custom_config = AtlasConfig()

        with patch("atlas.engine.runner.ScanRunner") as mock_runner_cls:
            mock_runner_instance = MagicMock()
            mock_runner_instance.run = AsyncMock(return_value=mock_result)
            mock_runner_cls.return_value = mock_runner_instance

            report = await scan(model="ignored", config=custom_config)

        mock_runner_cls.assert_called_once_with(custom_config)
        assert isinstance(report, ScanReport)

    @pytest.mark.asyncio
    async def test_scan_with_profile(self):
        """scan() should pass profile to runner."""
        mock_result = _make_scan_result()

        with patch("atlas.engine.runner.ScanRunner") as mock_runner_cls:
            mock_runner_instance = MagicMock()
            mock_runner_instance.run = AsyncMock(return_value=mock_result)
            mock_runner_cls.return_value = mock_runner_instance

            await scan(model="openai/gpt-4o", profile="comprehensive")

        mock_runner_instance.run.assert_awaited_once_with(
            profile="comprehensive",
            probe_names=None,
            detector_names=None,
        )


class TestScanSync:
    def test_scan_sync_runs_async_scan(self):
        """scan_sync() should be a synchronous wrapper around scan()."""
        mock_result = _make_scan_result()

        with patch("atlas.engine.runner.ScanRunner") as mock_runner_cls:
            mock_runner_instance = MagicMock()
            mock_runner_instance.run = AsyncMock(return_value=mock_result)
            mock_runner_cls.return_value = mock_runner_instance

            report = scan_sync(model="openai/gpt-4o", probes=["agent_harm"])

        assert isinstance(report, ScanReport)
        assert report.score == 75.0
