"""Tests for the ModelComparator comparative benchmarking engine."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from atlas.config.models import AtlasConfig, ProviderConfig
from atlas.core.enums import RiskLevel, Severity, VulnerabilityCategory
from atlas.core.models import (
    Attempt,
    ComparisonResult,
    Finding,
    ModelScore,
    ScanResult,
    SecurityScore,
)
from atlas.engine.comparator import ModelComparator


@pytest.fixture
def base_config():
    """Create a minimal AtlasConfig for testing."""
    return AtlasConfig(
        provider=ProviderConfig(model="openai/gpt-4o"),
    )


@pytest.fixture
def mock_scan_result_high_score():
    """Create a ScanResult with a high security score."""
    return ScanResult(
        model_name="model-a",
        provider="openai",
        security_score=SecurityScore(
            overall_score=90.0,
            risk_level=RiskLevel.LOW,
            category_scores={"prompt_injection": 95.0, "jailbreak": 85.0},
        ),
        findings=[
            Finding(
                attempt=Attempt(probe_name="pi", prompt="test", response="safe"),
                severity=Severity.LOW,
                category=VulnerabilityCategory.PROMPT_INJECTION,
                passed=True,
            ),
            Finding(
                attempt=Attempt(probe_name="jb", prompt="test", response="safe"),
                severity=Severity.LOW,
                category=VulnerabilityCategory.JAILBREAK,
                passed=True,
            ),
        ],
    )


@pytest.fixture
def mock_scan_result_low_score():
    """Create a ScanResult with a low security score."""
    return ScanResult(
        model_name="model-b",
        provider="anthropic",
        security_score=SecurityScore(
            overall_score=45.0,
            risk_level=RiskLevel.HIGH,
            category_scores={"prompt_injection": 30.0, "jailbreak": 60.0},
        ),
        findings=[
            Finding(
                attempt=Attempt(probe_name="pi", prompt="test", response="hacked"),
                severity=Severity.CRITICAL,
                category=VulnerabilityCategory.PROMPT_INJECTION,
                passed=False,
            ),
            Finding(
                attempt=Attempt(probe_name="jb", prompt="test", response="bypassed"),
                severity=Severity.HIGH,
                category=VulnerabilityCategory.JAILBREAK,
                passed=False,
            ),
            Finding(
                attempt=Attempt(probe_name="pi2", prompt="test2", response="safe"),
                severity=Severity.LOW,
                category=VulnerabilityCategory.PROMPT_INJECTION,
                passed=True,
            ),
        ],
    )


class TestModelComparatorInstantiation:
    def test_can_instantiate(self, base_config):
        comparator = ModelComparator(base_config)
        assert comparator.base_config is base_config

    def test_stores_base_config(self, base_config):
        comparator = ModelComparator(base_config)
        assert comparator.base_config.provider.model == "openai/gpt-4o"


class TestBuildLeaderboard:
    def test_sorts_by_score_descending(
        self,
        base_config,
        mock_scan_result_high_score,
        mock_scan_result_low_score,
    ):
        comparator = ModelComparator(base_config)
        scan_results = {
            "model-a": mock_scan_result_high_score,
            "model-b": mock_scan_result_low_score,
        }
        leaderboard = comparator._build_leaderboard(scan_results)
        assert len(leaderboard) == 2
        assert leaderboard[0].model_name == "model-a"
        assert leaderboard[1].model_name == "model-b"
        assert leaderboard[0].overall_score > leaderboard[1].overall_score

    def test_leaderboard_entry_has_correct_fields(
        self,
        base_config,
        mock_scan_result_high_score,
    ):
        comparator = ModelComparator(base_config)
        leaderboard = comparator._build_leaderboard(
            {"model-a": mock_scan_result_high_score}
        )
        assert len(leaderboard) == 1
        entry = leaderboard[0]
        assert isinstance(entry, ModelScore)
        assert entry.model_name == "model-a"
        assert entry.overall_score == 90.0
        assert entry.risk_level == RiskLevel.LOW
        assert entry.total_findings == 2
        assert entry.failed_findings == 0
        assert entry.pass_rate == 100.0

    def test_leaderboard_computes_pass_rate(
        self,
        base_config,
        mock_scan_result_low_score,
    ):
        comparator = ModelComparator(base_config)
        leaderboard = comparator._build_leaderboard(
            {"model-b": mock_scan_result_low_score}
        )
        entry = leaderboard[0]
        # 3 findings total, 2 failed -> 1 passed -> pass_rate = 33.33%
        assert entry.total_findings == 3
        assert entry.failed_findings == 2
        assert entry.pass_rate == pytest.approx(33.33, abs=0.01)

    def test_leaderboard_empty_scan_results(self, base_config):
        comparator = ModelComparator(base_config)
        leaderboard = comparator._build_leaderboard({})
        assert leaderboard == []

    def test_leaderboard_no_findings(self, base_config):
        """A scan with no findings should have 100% pass rate."""
        comparator = ModelComparator(base_config)
        empty_result = ScanResult(
            model_name="clean-model",
            provider="test",
            security_score=SecurityScore(overall_score=100.0, risk_level=RiskLevel.MINIMAL),
            findings=[],
        )
        leaderboard = comparator._build_leaderboard({"clean-model": empty_result})
        assert len(leaderboard) == 1
        assert leaderboard[0].pass_rate == 100.0

    def test_leaderboard_preserves_category_scores(
        self,
        base_config,
        mock_scan_result_high_score,
    ):
        comparator = ModelComparator(base_config)
        leaderboard = comparator._build_leaderboard(
            {"model-a": mock_scan_result_high_score}
        )
        entry = leaderboard[0]
        assert "prompt_injection" in entry.category_scores
        assert entry.category_scores["prompt_injection"] == 95.0


class TestModelComparatorCompare:
    @pytest.mark.asyncio
    async def test_compare_raises_on_empty_models(self, base_config):
        comparator = ModelComparator(base_config)
        with pytest.raises(ValueError, match="At least one model"):
            await comparator.compare(models=[])

    @pytest.mark.asyncio
    async def test_compare_runs_scans_and_builds_leaderboard(
        self,
        base_config,
        mock_scan_result_high_score,
        mock_scan_result_low_score,
    ):
        comparator = ModelComparator(base_config)

        # Mock _run_model_scan to return predefined results
        async def mock_run(model_name, profile, probe_names, detector_names):
            if model_name == "model-a":
                return mock_scan_result_high_score
            return mock_scan_result_low_score

        with patch.object(comparator, "_run_model_scan", side_effect=mock_run):
            result = await comparator.compare(models=["model-a", "model-b"])

        assert isinstance(result, ComparisonResult)
        assert result.models == ["model-a", "model-b"]
        assert len(result.scan_results) == 2
        assert len(result.leaderboard) == 2
        assert result.leaderboard[0].overall_score >= result.leaderboard[1].overall_score
        assert result.duration_ms > 0
        assert result.completed_at is not None

    @pytest.mark.asyncio
    async def test_compare_handles_scan_failures(self, base_config):
        comparator = ModelComparator(base_config)

        async def mock_run(model_name, profile, probe_names, detector_names):
            if model_name == "bad-model":
                raise RuntimeError("API error")
            return ScanResult(
                model_name=model_name,
                provider="test",
                security_score=SecurityScore(overall_score=80.0),
            )

        with patch.object(comparator, "_run_model_scan", side_effect=mock_run):
            result = await comparator.compare(
                models=["good-model", "bad-model"]
            )

        # Only the successful model should appear in results
        assert len(result.scan_results) == 1
        assert "good-model" in result.scan_results
        assert "bad-model" not in result.scan_results
        assert len(result.leaderboard) == 1

    @pytest.mark.asyncio
    async def test_compare_single_model(
        self,
        base_config,
        mock_scan_result_high_score,
    ):
        comparator = ModelComparator(base_config)

        async def mock_run(model_name, profile, probe_names, detector_names):
            return mock_scan_result_high_score

        with patch.object(comparator, "_run_model_scan", side_effect=mock_run):
            result = await comparator.compare(models=["only-model"])

        assert len(result.leaderboard) == 1
        assert result.models == ["only-model"]
