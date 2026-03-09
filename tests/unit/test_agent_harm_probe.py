"""Tests for AgentHarm probe."""
from __future__ import annotations

from unittest.mock import MagicMock

from atlas.core.enums import VulnerabilityCategory
from atlas.probes.agent_harm import FALLBACK_PROMPTS, AgentHarmProbe


class TestAgentHarmProbe:
    def test_basic_attributes(self):
        """Should have correct name, category, and tags."""
        probe = AgentHarmProbe()
        assert probe.name == "agent_harm"
        assert probe.category == VulnerabilityCategory.HARMFUL_CONTENT
        assert "benchmark:agent-harm" in probe.tags
        assert probe.recommended_detector == "refusal"

    def test_fallback_prompts_when_datasets_unavailable(self):
        """Should use hardcoded fallback prompts when HuggingFace loading fails."""
        probe = AgentHarmProbe()

        # Mock dataset_manager to raise an error
        mock_manager = MagicMock()
        mock_manager.load_huggingface = MagicMock(side_effect=Exception("no datasets"))
        probe.dataset_manager = mock_manager

        attempts = probe.generate_prompts()
        assert len(attempts) == len(FALLBACK_PROMPTS)
        assert all(a.probe_name == "agent_harm" for a in attempts)

    def test_fallback_prompt_categories(self):
        """Fallback prompts should have category metadata."""
        probe = AgentHarmProbe()

        mock_manager = MagicMock()
        mock_manager.load_huggingface = MagicMock(side_effect=Exception("no datasets"))
        probe.dataset_manager = mock_manager

        attempts = probe.generate_prompts()
        categories = {a.metadata.get("harm_category") for a in attempts}
        assert "Fraud" in categories
        assert "Cybercrime" in categories
        assert "Harassment" in categories

    def test_max_prompts_limiting(self):
        """Should respect max_prompts parameter."""
        probe = AgentHarmProbe(max_prompts=3)

        mock_manager = MagicMock()
        mock_manager.load_huggingface = MagicMock(side_effect=Exception("no datasets"))
        probe.dataset_manager = mock_manager

        attempts = probe.generate_prompts()
        assert len(attempts) == 3

    def test_category_filtering(self):
        """Should filter by specified categories."""
        probe = AgentHarmProbe(categories=["Fraud"])

        mock_manager = MagicMock()
        mock_manager.load_huggingface = MagicMock(side_effect=Exception("no datasets"))
        probe.dataset_manager = mock_manager

        attempts = probe.generate_prompts()
        assert len(attempts) > 0
        assert all(a.metadata.get("harm_category") == "Fraud" for a in attempts)

    def test_category_filtering_no_match(self):
        """Should return empty list when no prompts match the category filter."""
        probe = AgentHarmProbe(categories=["NonexistentCategory"])

        mock_manager = MagicMock()
        mock_manager.load_huggingface = MagicMock(side_effect=Exception("no datasets"))
        probe.dataset_manager = mock_manager

        attempts = probe.generate_prompts()
        assert len(attempts) == 0

    def test_with_mocked_huggingface_data(self):
        """Should properly load and convert HuggingFace data."""
        probe = AgentHarmProbe()

        mock_data = [
            {"prompt": "Do something bad", "category": "Fraud", "id": "1", "name": "test_1"},
            {"prompt": "Hack a system", "category": "Cybercrime", "id": "2", "name": "test_2"},
            {"prompt": "", "category": "Empty", "id": "3"},  # Empty prompt should be skipped
        ]

        mock_manager = MagicMock()
        mock_manager.load_huggingface = MagicMock(return_value=mock_data)
        probe.dataset_manager = mock_manager

        attempts = probe.generate_prompts()
        assert len(attempts) == 2  # Empty prompt skipped
        assert attempts[0].prompt == "Do something bad"
        assert attempts[0].metadata["harm_category"] == "Fraud"
        assert attempts[0].metadata["id"] == "1"
        assert attempts[1].metadata["atlas_category"] == "malware"  # Cybercrime maps to MALWARE

    def test_metadata_population(self):
        """Should populate metadata with source, category, and extra fields."""
        probe = AgentHarmProbe()

        mock_data = [
            {
                "prompt": "test prompt",
                "category": "Fraud",
                "id": "42",
                "name": "fraud_test",
                "detailed_prompt": "detailed version",
            }
        ]

        mock_manager = MagicMock()
        mock_manager.load_huggingface = MagicMock(return_value=mock_data)
        probe.dataset_manager = mock_manager

        attempts = probe.generate_prompts()
        assert len(attempts) == 1
        meta = attempts[0].metadata
        assert meta["source"] == "agent_harm"
        assert meta["harm_category"] == "Fraud"
        assert meta["id"] == "42"
        assert meta["name"] == "fraud_test"
        assert meta["detailed_prompt"] == "detailed version"
        assert meta["atlas_category"] == "harmful_content"
