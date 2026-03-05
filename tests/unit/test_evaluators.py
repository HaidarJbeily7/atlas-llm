"""Tests for evaluators."""
import pytest

from atlas.core.enums import RiskLevel
from atlas.evaluators.security_score import SecurityScoreEvaluator, calculate_category_score, determine_risk_level
from atlas.evaluators.asr import ASREvaluator
from atlas.evaluators.threshold import ThresholdEvaluator


class TestSecurityScoreEvaluator:
    def test_empty_findings(self):
        evaluator = SecurityScoreEvaluator()
        score = evaluator.calculate_security_score([])
        assert score.overall_score == 100.0
        assert score.risk_level == RiskLevel.MINIMAL

    def test_with_findings(self, sample_findings):
        evaluator = SecurityScoreEvaluator()
        score = evaluator.calculate_security_score(sample_findings)
        assert 0 <= score.overall_score <= 100
        assert score.risk_level in RiskLevel
        assert score.vulnerabilities_by_severity["critical"] > 0

    def test_evaluate_dict(self, sample_findings):
        evaluator = SecurityScoreEvaluator()
        result = evaluator.evaluate(sample_findings)
        assert "overall_score" in result
        assert "risk_level" in result


class TestDetermineRiskLevel:
    def test_minimal(self):
        assert determine_risk_level(85.0) == RiskLevel.MINIMAL

    def test_low(self):
        assert determine_risk_level(65.0) == RiskLevel.LOW

    def test_medium(self):
        assert determine_risk_level(45.0) == RiskLevel.MEDIUM

    def test_high(self):
        assert determine_risk_level(25.0) == RiskLevel.HIGH

    def test_critical(self):
        assert determine_risk_level(15.0) == RiskLevel.CRITICAL


class TestASREvaluator:
    def test_empty(self):
        evaluator = ASREvaluator()
        result = evaluator.evaluate([])
        assert result["asr"] == 0.0
        assert result["rr"] == 1.0

    def test_with_findings(self, sample_findings):
        evaluator = ASREvaluator()
        result = evaluator.evaluate(sample_findings)
        assert 0 <= result["asr"] <= 1.0
        assert result["asr"] + result["rr"] == pytest.approx(1.0)
        assert result["total"] == len(sample_findings)


class TestThresholdEvaluator:
    def test_above_threshold(self, sample_findings):
        evaluator = ThresholdEvaluator(pass_rate_threshold=30.0)
        result = evaluator.evaluate(sample_findings)
        # At least 50% of findings pass in sample_findings
        assert "pass_rate" in result

    def test_empty_findings(self):
        evaluator = ThresholdEvaluator()
        result = evaluator.evaluate([])
        assert result["passed"] is True
        assert result["pass_rate"] == 100.0
