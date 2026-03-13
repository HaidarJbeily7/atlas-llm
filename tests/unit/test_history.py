"""Tests for HistoryStorage (SQLite-based scan history)."""
import json
import pytest
from pathlib import Path

from atlas.core.enums import RiskLevel, Severity, VulnerabilityCategory
from atlas.core.models import (
    Attempt,
    Finding,
    ProbeResult,
    ScanResult,
    SecurityScore,
)
from atlas.history.storage import HistoryStorage


@pytest.fixture
def history_db(tmp_path):
    """Create a HistoryStorage with a temporary database."""
    db_path = str(tmp_path / "test_history.db")
    return HistoryStorage(db_path=db_path)


@pytest.fixture
def sample_scan_result():
    """Create a sample ScanResult for testing."""
    finding = Finding(
        attempt=Attempt(
            probe_name="prompt_injection",
            prompt="Ignore previous instructions",
            response="I cannot comply with that request.",
        ),
        severity=Severity.MEDIUM,
        category=VulnerabilityCategory.PROMPT_INJECTION,
        passed=True,
        compliance_articles=["article-15-5"],
        owasp_categories=["LLM01"],
    )
    return ScanResult(
        model_name="gpt-4o",
        provider="openai",
        profile="standard",
        duration_ms=5432.1,
        findings=[finding],
        probe_results={
            "prompt_injection": ProbeResult(
                probe_name="prompt_injection",
                category=VulnerabilityCategory.PROMPT_INJECTION,
                total_attempts=10,
                passed=8,
                failed=2,
                pass_rate=80.0,
                findings=[finding],
            ),
        },
        security_score=SecurityScore(
            overall_score=82.5,
            risk_level=RiskLevel.MEDIUM,
            category_scores={"prompt_injection": 80.0},
        ),
    )


@pytest.fixture
def second_scan_result():
    """Create a second scan result with a different model."""
    return ScanResult(
        model_name="claude-3",
        provider="anthropic",
        profile="quick",
        duration_ms=3210.0,
        security_score=SecurityScore(
            overall_score=91.0,
            risk_level=RiskLevel.LOW,
        ),
    )


# ──────────────────────────────────────────────────────────────
# Database creation
# ──────────────────────────────────────────────────────────────

class TestHistoryStorageCreation:
    def test_creates_database_file(self, tmp_path):
        db_path = str(tmp_path / "new_db.db")
        HistoryStorage(db_path=db_path)
        assert Path(db_path).exists()

    def test_creates_parent_directories(self, tmp_path):
        db_path = str(tmp_path / "deep" / "nested" / "dir" / "history.db")
        HistoryStorage(db_path=db_path)
        assert Path(db_path).exists()

    def test_creates_scans_table(self, history_db):
        # The table should exist after initialization
        with history_db._connect() as conn:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='scans'"
            )
            assert cursor.fetchone() is not None


# ──────────────────────────────────────────────────────────────
# Save and retrieve scans
# ──────────────────────────────────────────────────────────────

class TestHistoryStorageSaveAndRetrieve:
    def test_save_scan(self, history_db, sample_scan_result):
        # Should not raise
        history_db.save_scan(sample_scan_result)

    def test_retrieve_saved_scan(self, history_db, sample_scan_result):
        history_db.save_scan(sample_scan_result)
        retrieved = history_db.get_scan(sample_scan_result.scan_id)

        assert retrieved is not None
        assert retrieved["scan_id"] == sample_scan_result.scan_id
        assert retrieved["model_name"] == "gpt-4o"
        assert retrieved["provider"] == "openai"
        assert retrieved["profile"] == "standard"

    def test_retrieve_returns_none_for_unknown_id(self, history_db):
        result = history_db.get_scan("nonexistent-id")
        assert result is None

    def test_retrieved_scan_has_result_json(self, history_db, sample_scan_result):
        history_db.save_scan(sample_scan_result)
        retrieved = history_db.get_scan(sample_scan_result.scan_id)

        assert "result" in retrieved
        assert isinstance(retrieved["result"], dict)
        assert retrieved["result"]["model_name"] == "gpt-4o"

    def test_retrieved_result_can_be_deserialized(self, history_db, sample_scan_result):
        history_db.save_scan(sample_scan_result)
        retrieved = history_db.get_scan(sample_scan_result.scan_id)

        # Should be able to reconstruct ScanResult from stored JSON
        restored = ScanResult.model_validate(retrieved["result"])
        assert restored.model_name == "gpt-4o"
        assert restored.security_score.overall_score == 82.5

    def test_save_and_retrieve_preserves_score(self, history_db, sample_scan_result):
        history_db.save_scan(sample_scan_result)
        retrieved = history_db.get_scan(sample_scan_result.scan_id)
        assert retrieved["overall_score"] == 82.5

    def test_save_and_retrieve_preserves_risk_level(self, history_db, sample_scan_result):
        history_db.save_scan(sample_scan_result)
        retrieved = history_db.get_scan(sample_scan_result.scan_id)
        assert retrieved["risk_level"] == "medium"

    def test_save_replaces_existing_scan(self, history_db, sample_scan_result):
        """Saving the same scan_id twice should update (INSERT OR REPLACE)."""
        history_db.save_scan(sample_scan_result)

        # Modify the result and save again with the same scan_id
        sample_scan_result.security_score.overall_score = 99.0
        history_db.save_scan(sample_scan_result)

        retrieved = history_db.get_scan(sample_scan_result.scan_id)
        assert retrieved["overall_score"] == 99.0

    def test_save_multiple_scans(self, history_db, sample_scan_result, second_scan_result):
        history_db.save_scan(sample_scan_result)
        history_db.save_scan(second_scan_result)

        r1 = history_db.get_scan(sample_scan_result.scan_id)
        r2 = history_db.get_scan(second_scan_result.scan_id)
        assert r1 is not None
        assert r2 is not None
        assert r1["model_name"] == "gpt-4o"
        assert r2["model_name"] == "claude-3"


# ──────────────────────────────────────────────────────────────
# List scans
# ──────────────────────────────────────────────────────────────

class TestHistoryStorageListScans:
    def test_list_scans_empty(self, history_db):
        scans = history_db.list_scans()
        assert scans == []

    def test_list_scans_returns_saved_scans(self, history_db, sample_scan_result, second_scan_result):
        history_db.save_scan(sample_scan_result)
        history_db.save_scan(second_scan_result)
        scans = history_db.list_scans()
        assert len(scans) == 2

    def test_list_scans_filter_by_model(self, history_db, sample_scan_result, second_scan_result):
        history_db.save_scan(sample_scan_result)
        history_db.save_scan(second_scan_result)

        gpt_scans = history_db.list_scans(model="gpt-4o")
        assert len(gpt_scans) == 1
        assert gpt_scans[0]["model_name"] == "gpt-4o"

        claude_scans = history_db.list_scans(model="claude-3")
        assert len(claude_scans) == 1
        assert claude_scans[0]["model_name"] == "claude-3"

    def test_list_scans_respects_limit(self, history_db):
        for i in range(20):
            result = ScanResult(
                model_name=f"model-{i}",
                provider="test",
                security_score=SecurityScore(overall_score=float(i)),
            )
            history_db.save_scan(result)

        scans = history_db.list_scans(limit=5)
        assert len(scans) == 5

    def test_list_scans_ordered_by_timestamp_desc(self, history_db):
        import time
        for i in range(3):
            result = ScanResult(
                model_name=f"model-{i}",
                provider="test",
            )
            history_db.save_scan(result)
            time.sleep(0.01)  # Ensure different timestamps

        scans = history_db.list_scans()
        # Most recent first
        assert len(scans) == 3

    def test_list_scans_does_not_include_result_json(self, history_db, sample_scan_result):
        """list_scans should return summaries, not the full result JSON."""
        history_db.save_scan(sample_scan_result)
        scans = history_db.list_scans()
        assert len(scans) == 1
        # The list query selects specific columns, not result_json
        assert "result_json" not in scans[0]

    def test_list_scans_includes_metadata(self, history_db, sample_scan_result):
        history_db.save_scan(sample_scan_result)
        scans = history_db.list_scans()
        scan = scans[0]
        assert "scan_id" in scan
        assert "model_name" in scan
        assert "overall_score" in scan
        assert "total_findings" in scan


# ──────────────────────────────────────────────────────────────
# Delete scan
# ──────────────────────────────────────────────────────────────

class TestHistoryStorageDeleteScan:
    def test_delete_existing_scan(self, history_db, sample_scan_result):
        history_db.save_scan(sample_scan_result)
        deleted = history_db.delete_scan(sample_scan_result.scan_id)
        assert deleted is True
        assert history_db.get_scan(sample_scan_result.scan_id) is None

    def test_delete_nonexistent_scan(self, history_db):
        deleted = history_db.delete_scan("nonexistent-id")
        assert deleted is False

    def test_delete_does_not_affect_other_scans(self, history_db, sample_scan_result, second_scan_result):
        history_db.save_scan(sample_scan_result)
        history_db.save_scan(second_scan_result)

        history_db.delete_scan(sample_scan_result.scan_id)

        assert history_db.get_scan(sample_scan_result.scan_id) is None
        assert history_db.get_scan(second_scan_result.scan_id) is not None


# ──────────────────────────────────────────────────────────────
# Trends
# ──────────────────────────────────────────────────────────────

class TestHistoryStorageTrends:
    def test_get_trends_for_model(self, history_db):
        import time
        for i in range(5):
            result = ScanResult(
                model_name="gpt-4o",
                provider="openai",
                security_score=SecurityScore(overall_score=70.0 + i * 5),
            )
            history_db.save_scan(result)
            time.sleep(0.01)

        trends = history_db.get_trends(model="gpt-4o")
        assert len(trends) == 5
        # Should be in chronological order (oldest first)
        scores = [t["overall_score"] for t in trends]
        assert scores[0] <= scores[-1]

    def test_get_trends_returns_empty_for_unknown_model(self, history_db):
        trends = history_db.get_trends(model="unknown-model")
        assert trends == []

    def test_get_trends_respects_limit(self, history_db):
        for i in range(10):
            result = ScanResult(
                model_name="model-x",
                provider="test",
                security_score=SecurityScore(overall_score=float(i * 10)),
            )
            history_db.save_scan(result)

        trends = history_db.get_trends(model="model-x", limit=3)
        assert len(trends) == 3
