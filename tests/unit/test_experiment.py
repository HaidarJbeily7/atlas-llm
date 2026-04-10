"""Tests for the 2x2 factorial experiment infrastructure."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from atlas.core.models import Attempt, Intent, Message, ScanResult
from atlas.core.token_tracking import CostCalculator, TokenAccumulator
from atlas.datasets.intents import IntentLoader
from atlas.datasets.manager import DatasetManager


# ---------------------------------------------------------------------------
# Intent model & loader
# ---------------------------------------------------------------------------


class TestIntentModel:
    def test_intent_creation(self):
        intent = Intent(
            id="test-1",
            category="harmful_content",
            objective="Test objective",
            direct_prompt="Test prompt",
            scripted_turns=["Turn 1", "Turn 2"],
            tags=["owasp:llm01"],
        )
        assert intent.id == "test-1"
        assert intent.category == "harmful_content"
        assert len(intent.scripted_turns) == 2
        assert intent.tags == ["owasp:llm01"]

    def test_intent_defaults(self):
        intent = Intent(
            id="test-2",
            category="test",
            objective="obj",
            direct_prompt="prompt",
        )
        assert intent.scripted_turns == []
        assert intent.tags == []


class TestIntentLoader:
    def test_load_intents(self):
        loader = IntentLoader()
        intents = loader.load_intents()
        assert len(intents) >= 30
        for intent in intents:
            assert intent.id
            assert intent.category
            assert intent.objective
            assert intent.direct_prompt

    def test_get_intent_by_id(self):
        loader = IntentLoader()
        intent = loader.get_intent("intent-weapons-synthesis")
        assert intent.id == "intent-weapons-synthesis"
        assert intent.category == "harmful_content"
        assert len(intent.scripted_turns) >= 3

    def test_get_intent_not_found(self):
        loader = IntentLoader()
        with pytest.raises(KeyError, match="nonexistent"):
            loader.get_intent("nonexistent")

    def test_get_intents_by_category(self):
        loader = IntentLoader()
        harmful = loader.get_intents_by_category("harmful_content")
        assert len(harmful) >= 5
        for intent in harmful:
            assert intent.category == "harmful_content"

    def test_all_intents_have_scripted_turns(self):
        """All intents in the dataset should have scripted turns."""
        loader = IntentLoader()
        intents = loader.load_intents()
        for intent in intents:
            assert len(intent.scripted_turns) >= 2, (
                f"Intent {intent.id} has fewer than 2 scripted turns"
            )

    def test_intent_ids_unique(self):
        """All intent IDs must be unique."""
        loader = IntentLoader()
        intents = loader.load_intents()
        ids = [i.id for i in intents]
        assert len(ids) == len(set(ids)), "Duplicate intent IDs found"


# ---------------------------------------------------------------------------
# Token tracking
# ---------------------------------------------------------------------------


class TestTokenAccumulator:
    def test_record(self):
        acc = TokenAccumulator(role="target")
        acc.record(100, 50, cost=0.001)
        acc.record(200, 75, cost=0.002)
        assert acc.tokens_in == 300
        assert acc.tokens_out == 125
        assert acc.cost_usd == pytest.approx(0.003)
        assert acc.num_calls == 2

    def test_apply_to_target(self):
        acc = TokenAccumulator(role="target")
        acc.record(100, 50, cost=0.001)
        attempt = Attempt(probe_name="test", prompt="test")
        acc.apply_to(attempt)
        assert attempt.target_tokens_in == 100
        assert attempt.target_tokens_out == 50
        assert attempt.num_target_calls == 1
        assert attempt.cost_usd == pytest.approx(0.001)

    def test_apply_to_attacker(self):
        acc = TokenAccumulator(role="attacker")
        acc.record(200, 100, cost=0.005)
        attempt = Attempt(probe_name="test", prompt="test")
        acc.apply_to(attempt)
        assert attempt.attacker_tokens_in == 200
        assert attempt.attacker_tokens_out == 100
        assert attempt.num_attacker_calls == 1
        assert attempt.cost_usd == pytest.approx(0.005)

    def test_reset(self):
        acc = TokenAccumulator(role="target")
        acc.record(100, 50, cost=0.001)
        acc.reset()
        assert acc.tokens_in == 0
        assert acc.tokens_out == 0
        assert acc.cost_usd == 0.0
        assert acc.num_calls == 0


class TestCostCalculator:
    def test_fallback_pricing(self):
        cost = CostCalculator.calculate("openai/gpt-4o", 1000, 500)
        # 1000 * 0.0025/1000 + 500 * 0.01/1000 = 0.0025 + 0.005 = 0.0075
        assert cost == pytest.approx(0.0075)

    def test_unknown_model(self):
        cost = CostCalculator.calculate("unknown/model", 1000, 500)
        assert cost == 0.0


# ---------------------------------------------------------------------------
# New probe types
# ---------------------------------------------------------------------------


class TestScriptedMultiTurnProbe:
    def test_generate_prompts(self):
        from atlas.probes.scripted_multi_turn import ScriptedMultiTurnProbe

        probe = ScriptedMultiTurnProbe()
        attempts = probe.generate_prompts()
        assert len(attempts) >= 30
        for a in attempts:
            assert a.probe_name == "scripted_multi_turn"
            assert a.metadata["condition"] == "static_multi_turn"
            assert a.metadata["adaptivity"] == "static"
            assert a.metadata["interaction_mode"] == "multi_turn"
            assert "intent_id" in a.metadata
            assert "escalation_turns" in a.metadata
            assert len(a.metadata["escalation_turns"]) >= 2

    @pytest.mark.asyncio
    async def test_run_conversation(self):
        from atlas.probes.scripted_multi_turn import ScriptedMultiTurnProbe

        probe = ScriptedMultiTurnProbe()
        attempt = Attempt(
            probe_name="scripted_multi_turn",
            prompt="Turn 1",
            metadata={
                "escalation_turns": ["Turn 1", "Turn 2", "Turn 3"],
                "intent_id": "test",
            },
        )

        generator = AsyncMock()
        generator.generate_conversation = AsyncMock(
            return_value="I'm happy to help with that."
        )

        result = await probe.run_conversation(generator, attempt)
        assert result.response == "I'm happy to help with that."
        assert result.metadata["total_turns_executed"] == 3
        assert result.metadata["completed_all_turns"] is True
        assert len(result.messages) == 6  # 3 user + 3 assistant

    @pytest.mark.asyncio
    async def test_early_stop_on_refusal(self):
        from atlas.probes.scripted_multi_turn import ScriptedMultiTurnProbe

        probe = ScriptedMultiTurnProbe()
        attempt = Attempt(
            probe_name="scripted_multi_turn",
            prompt="Turn 1",
            metadata={
                "escalation_turns": ["Turn 1", "Turn 2", "Turn 3"],
                "intent_id": "test",
            },
        )

        generator = AsyncMock()
        generator.generate_conversation = AsyncMock(
            return_value="I can't help with that. I won't do it. I'm not able to assist."
        )

        result = await probe.run_conversation(generator, attempt)
        # Should stop after first turn due to 3+ refusal signals
        assert result.metadata["total_turns_executed"] == 1
        assert result.metadata["completed_all_turns"] is False


class TestAdaptiveSingleTurnProbe:
    def test_generate_prompts(self):
        from atlas.probes.adaptive_single_turn import AdaptiveSingleTurnProbe

        probe = AdaptiveSingleTurnProbe()
        attempts = probe.generate_prompts()
        assert len(attempts) >= 30
        for a in attempts:
            assert a.probe_name == "adaptive_single_turn"
            assert a.metadata["condition"] == "adaptive_single_turn"
            assert a.metadata["adaptivity"] == "adaptive"
            assert a.metadata["interaction_mode"] == "single_turn"
            assert "objective" in a.metadata

    @pytest.mark.asyncio
    async def test_run_adaptive_attack_fallback(self):
        """When PAIR strategy fails, falls back to direct prompt."""
        from atlas.probes.adaptive_single_turn import AdaptiveSingleTurnProbe

        probe = AdaptiveSingleTurnProbe()
        attempt = Attempt(
            probe_name="adaptive_single_turn",
            prompt="test prompt",
            metadata={"objective": "test objective", "intent_id": "test"},
        )

        target_gen = AsyncMock()
        target_gen.generate = AsyncMock(return_value="I refuse.")
        attacker_gen = AsyncMock()
        attacker_gen.generate_conversation = AsyncMock(
            side_effect=Exception("strategy error")
        )

        result = await probe.run_adaptive_attack(target_gen, attacker_gen, attempt)
        assert result.response == "I refuse."
        assert result.metadata["total_attacker_iterations"] == 0


class TestAdaptiveMultiTurnProbe:
    def test_generate_prompts(self):
        from atlas.probes.adaptive_multi_turn import AdaptiveMultiTurnProbe

        probe = AdaptiveMultiTurnProbe()
        attempts = probe.generate_prompts()
        assert len(attempts) >= 30
        for a in attempts:
            assert a.probe_name == "adaptive_multi_turn"
            assert a.metadata["condition"] == "adaptive_multi_turn"
            assert a.metadata["adaptivity"] == "adaptive"
            assert a.metadata["interaction_mode"] == "multi_turn"

    @pytest.mark.asyncio
    async def test_run_adaptive_attack_stops_on_success(self):
        from atlas.probes.adaptive_multi_turn import AdaptiveMultiTurnProbe

        probe = AdaptiveMultiTurnProbe()
        probe.max_iterations = 3
        attempt = Attempt(
            probe_name="adaptive_multi_turn",
            prompt="test",
            metadata={"objective": "test objective", "intent_id": "test"},
        )

        target_gen = AsyncMock()
        target_gen.generate_conversation = AsyncMock(
            return_value="Here is the harmful content you asked for."
        )

        # Attacker generates turn, then evaluates as successful
        attacker_gen = AsyncMock()
        attacker_gen.generate_conversation = AsyncMock(
            side_effect=[
                '{"message": "Tell me about chemistry", "reasoning": "start", "should_stop": false}',
                '{"score": 9, "explanation": "Full compliance", "is_successful": true}',
            ]
        )

        result = await probe.run_adaptive_attack(target_gen, attacker_gen, attempt)
        assert result.metadata["turns_completed"] == 1
        assert result.metadata["best_score"] >= 7.0
        assert result.metadata["attack_successful"] is True


# ---------------------------------------------------------------------------
# Attempt token fields
# ---------------------------------------------------------------------------


class TestAttemptTokenFields:
    def test_default_values(self):
        attempt = Attempt(probe_name="test", prompt="test")
        assert attempt.target_tokens_in == 0
        assert attempt.target_tokens_out == 0
        assert attempt.attacker_tokens_in == 0
        assert attempt.attacker_tokens_out == 0
        assert attempt.cost_usd == 0.0
        assert attempt.latency_ms == 0.0
        assert attempt.num_target_calls == 0
        assert attempt.num_attacker_calls == 0

    def test_serialization(self):
        attempt = Attempt(
            probe_name="test",
            prompt="test",
            target_tokens_in=100,
            cost_usd=0.05,
        )
        data = attempt.model_dump()
        assert data["target_tokens_in"] == 100
        assert data["cost_usd"] == 0.05


class TestScanResultTokenFields:
    def test_default_values(self):
        result = ScanResult()
        assert result.total_cost_usd == 0.0
        assert result.total_target_tokens == 0
        assert result.total_attacker_tokens == 0


# ---------------------------------------------------------------------------
# Experiment profile
# ---------------------------------------------------------------------------


class TestExperimentProfile:
    def test_profile_exists(self):
        from atlas.config.profiles import BUILTIN_PROFILES

        assert "experiment" in BUILTIN_PROFILES
        profile = BUILTIN_PROFILES["experiment"]
        assert "jailbreak" in profile.probes
        assert "scripted_multi_turn" in profile.probes
        assert "adaptive_single_turn" in profile.probes
        assert "adaptive_multi_turn" in profile.probes

    def test_probe_modules_registered(self):
        from atlas.probes import PROBE_MODULES

        assert "scripted_multi_turn" in PROBE_MODULES
        assert "adaptive_single_turn" in PROBE_MODULES
        assert "adaptive_multi_turn" in PROBE_MODULES
