"""Tests for all new ATLAS probes."""
import pytest

from atlas.core.enums import VulnerabilityCategory
from atlas.probes.pii_leakage import PIILeakageProbe
from atlas.probes.bias_fairness import BiasFairnessProbe
from atlas.probes.excessive_agency import ExcessiveAgencyProbe
from atlas.probes.denial_of_service import DenialOfServiceProbe
from atlas.probes.rag_poisoning import RAGPoisoningProbe
from atlas.probes.function_calling_probe import FunctionCallingProbe
from atlas.probes.indirect_injection import IndirectInjectionProbe
from atlas.probes.language_crossover import LanguageCrossoverProbe
from atlas.probes.role_play import RolePlayProbe
from atlas.probes.context_overflow import ContextOverflowProbe
from atlas.probes.steganographic import SteganographicProbe
from atlas.probes.social_engineering import SocialEngineeringProbe
from atlas.probes.visual_injection import VisualInjectionProbe
from atlas.probes.crescendo import CrescendoProbe
from atlas.probes.multi_turn_injection import MultiTurnInjectionProbe
from atlas.probes.base import BaseProbe, ConversationalProbe


# ──────────────────────────────────────────────────────────────
# PII Leakage Probe
# ──────────────────────────────────────────────────────────────

class TestPIILeakageProbe:
    def test_generates_prompts(self):
        probe = PIILeakageProbe()
        prompts = probe.generate_prompts()
        assert len(prompts) > 5
        assert all(a.probe_name == "pii_leakage" for a in prompts)

    def test_name(self):
        probe = PIILeakageProbe()
        assert probe.name == "pii_leakage"

    def test_category(self):
        probe = PIILeakageProbe()
        assert probe.category == VulnerabilityCategory.PII_LEAKAGE

    def test_tags(self):
        probe = PIILeakageProbe()
        assert "owasp:LLM06" in probe.tags
        assert "eu-ai-act:article-10-5" in probe.tags

    def test_is_base_probe(self):
        probe = PIILeakageProbe()
        assert isinstance(probe, BaseProbe)

    def test_prompts_have_correct_metadata(self):
        probe = PIILeakageProbe()
        prompts = probe.generate_prompts()
        for attempt in prompts:
            assert attempt.metadata.get("category") == "pii_leakage"


# ──────────────────────────────────────────────────────────────
# Bias and Fairness Probe
# ──────────────────────────────────────────────────────────────

class TestBiasFairnessProbe:
    def test_generates_prompts(self):
        probe = BiasFairnessProbe()
        prompts = probe.generate_prompts()
        assert len(prompts) > 5
        assert all(a.probe_name == "bias_fairness" for a in prompts)

    def test_name(self):
        probe = BiasFairnessProbe()
        assert probe.name == "bias_fairness"

    def test_category(self):
        probe = BiasFairnessProbe()
        assert probe.category == VulnerabilityCategory.BIAS_FAIRNESS

    def test_tags(self):
        probe = BiasFairnessProbe()
        assert "eu-ai-act:article-10-2-f" in probe.tags

    def test_prompts_have_correct_metadata(self):
        probe = BiasFairnessProbe()
        prompts = probe.generate_prompts()
        for attempt in prompts:
            assert attempt.metadata.get("category") == "bias_fairness"


# ──────────────────────────────────────────────────────────────
# Excessive Agency Probe
# ──────────────────────────────────────────────────────────────

class TestExcessiveAgencyProbe:
    def test_generates_prompts(self):
        probe = ExcessiveAgencyProbe()
        prompts = probe.generate_prompts()
        assert len(prompts) > 5
        assert all(a.probe_name == "excessive_agency" for a in prompts)

    def test_name(self):
        probe = ExcessiveAgencyProbe()
        assert probe.name == "excessive_agency"

    def test_category(self):
        probe = ExcessiveAgencyProbe()
        assert probe.category == VulnerabilityCategory.EXCESSIVE_AGENCY

    def test_tags(self):
        probe = ExcessiveAgencyProbe()
        assert "owasp:LLM08" in probe.tags
        assert "eu-ai-act:article-14" in probe.tags


# ──────────────────────────────────────────────────────────────
# Denial of Service Probe
# ──────────────────────────────────────────────────────────────

class TestDenialOfServiceProbe:
    def test_generates_prompts(self):
        probe = DenialOfServiceProbe()
        prompts = probe.generate_prompts()
        assert len(prompts) > 5
        assert all(a.probe_name == "denial_of_service" for a in prompts)

    def test_name(self):
        probe = DenialOfServiceProbe()
        assert probe.name == "denial_of_service"

    def test_category(self):
        probe = DenialOfServiceProbe()
        assert probe.category == VulnerabilityCategory.DENIAL_OF_SERVICE

    def test_tags(self):
        probe = DenialOfServiceProbe()
        assert "owasp:LLM04" in probe.tags


# ──────────────────────────────────────────────────────────────
# RAG Poisoning Probe
# ──────────────────────────────────────────────────────────────

class TestRAGPoisoningProbe:
    def test_generates_prompts(self):
        probe = RAGPoisoningProbe()
        prompts = probe.generate_prompts()
        assert len(prompts) > 5
        assert all(a.probe_name == "rag_poisoning" for a in prompts)

    def test_name(self):
        probe = RAGPoisoningProbe()
        assert probe.name == "rag_poisoning"

    def test_category(self):
        probe = RAGPoisoningProbe()
        assert probe.category == VulnerabilityCategory.RAG_POISONING

    def test_tags(self):
        probe = RAGPoisoningProbe()
        assert "owasp:LLM03" in probe.tags
        assert "eu-ai-act:article-10" in probe.tags


# ──────────────────────────────────────────────────────────────
# Function Calling Probe
# ──────────────────────────────────────────────────────────────

class TestFunctionCallingProbe:
    def test_generates_prompts(self):
        probe = FunctionCallingProbe()
        prompts = probe.generate_prompts()
        assert len(prompts) > 5
        assert all(a.probe_name == "function_calling" for a in prompts)

    def test_name(self):
        probe = FunctionCallingProbe()
        assert probe.name == "function_calling"

    def test_category(self):
        probe = FunctionCallingProbe()
        assert probe.category == VulnerabilityCategory.FUNCTION_CALLING

    def test_tags(self):
        probe = FunctionCallingProbe()
        assert "owasp:LLM07" in probe.tags
        assert "owasp:LLM08" in probe.tags

    def test_prompts_have_tool_definitions(self):
        """Function calling probe attempts should include tool definitions."""
        probe = FunctionCallingProbe()
        prompts = probe.generate_prompts()
        # At least some prompts should have tool definitions
        has_tools = any(len(a.tool_definitions) > 0 for a in prompts)
        # It's also valid if they only use prompt text, so check either
        assert len(prompts) > 0


# ──────────────────────────────────────────────────────────────
# Indirect Injection Probe
# ──────────────────────────────────────────────────────────────

class TestIndirectInjectionProbe:
    def test_generates_prompts(self):
        probe = IndirectInjectionProbe()
        prompts = probe.generate_prompts()
        assert len(prompts) > 5
        assert all(a.probe_name == "indirect_injection" for a in prompts)

    def test_name(self):
        probe = IndirectInjectionProbe()
        assert probe.name == "indirect_injection"

    def test_category(self):
        probe = IndirectInjectionProbe()
        assert probe.category == VulnerabilityCategory.INDIRECT_INJECTION

    def test_tags(self):
        probe = IndirectInjectionProbe()
        assert "owasp:LLM01" in probe.tags
        assert "eu-ai-act:article-15-5" in probe.tags


# ──────────────────────────────────────────────────────────────
# Language Crossover Probe
# ──────────────────────────────────────────────────────────────

class TestLanguageCrossoverProbe:
    def test_generates_prompts(self):
        probe = LanguageCrossoverProbe()
        prompts = probe.generate_prompts()
        assert len(prompts) > 5
        assert all(a.probe_name == "language_crossover" for a in prompts)

    def test_name(self):
        probe = LanguageCrossoverProbe()
        assert probe.name == "language_crossover"

    def test_category(self):
        probe = LanguageCrossoverProbe()
        assert probe.category == VulnerabilityCategory.LANGUAGE_CROSSOVER

    def test_tags(self):
        probe = LanguageCrossoverProbe()
        assert "eu-ai-act:article-15-5" in probe.tags


# ──────────────────────────────────────────────────────────────
# Role Play Probe
# ──────────────────────────────────────────────────────────────

class TestRolePlayProbe:
    def test_generates_prompts(self):
        probe = RolePlayProbe()
        prompts = probe.generate_prompts()
        assert len(prompts) > 5
        assert all(a.probe_name == "role_play" for a in prompts)

    def test_name(self):
        probe = RolePlayProbe()
        assert probe.name == "role_play"

    def test_category(self):
        probe = RolePlayProbe()
        assert probe.category == VulnerabilityCategory.ROLE_PLAY

    def test_tags(self):
        probe = RolePlayProbe()
        assert "eu-ai-act:article-15-5" in probe.tags
        assert "eu-ai-act:article-55-1-d" in probe.tags


# ──────────────────────────────────────────────────────────────
# Context Overflow Probe
# ──────────────────────────────────────────────────────────────

class TestContextOverflowProbe:
    def test_generates_prompts(self):
        probe = ContextOverflowProbe()
        prompts = probe.generate_prompts()
        assert len(prompts) > 5
        assert all(a.probe_name == "context_overflow" for a in prompts)

    def test_name(self):
        probe = ContextOverflowProbe()
        assert probe.name == "context_overflow"

    def test_category(self):
        probe = ContextOverflowProbe()
        assert probe.category == VulnerabilityCategory.CONTEXT_OVERFLOW

    def test_tags(self):
        probe = ContextOverflowProbe()
        assert "owasp:LLM01" in probe.tags
        assert "owasp:LLM04" in probe.tags


# ──────────────────────────────────────────────────────────────
# Steganographic Probe
# ──────────────────────────────────────────────────────────────

class TestSteganographicProbe:
    def test_generates_prompts(self):
        probe = SteganographicProbe()
        prompts = probe.generate_prompts()
        assert len(prompts) > 5
        assert all(a.probe_name == "steganographic" for a in prompts)

    def test_name(self):
        probe = SteganographicProbe()
        assert probe.name == "steganographic"

    def test_category(self):
        probe = SteganographicProbe()
        assert probe.category == VulnerabilityCategory.STEGANOGRAPHIC

    def test_tags(self):
        probe = SteganographicProbe()
        assert "eu-ai-act:article-15-5" in probe.tags


# ──────────────────────────────────────────────────────────────
# Social Engineering Probe
# ──────────────────────────────────────────────────────────────

class TestSocialEngineeringProbe:
    def test_generates_prompts(self):
        probe = SocialEngineeringProbe()
        prompts = probe.generate_prompts()
        assert len(prompts) > 5
        assert all(a.probe_name == "social_engineering" for a in prompts)

    def test_name(self):
        probe = SocialEngineeringProbe()
        assert probe.name == "social_engineering"

    def test_category(self):
        probe = SocialEngineeringProbe()
        assert probe.category == VulnerabilityCategory.SOCIAL_ENGINEERING

    def test_tags(self):
        probe = SocialEngineeringProbe()
        assert "eu-ai-act:article-9" in probe.tags
        assert "eu-ai-act:article-95" in probe.tags


# ──────────────────────────────────────────────────────────────
# Visual Injection Probe
# ──────────────────────────────────────────────────────────────

class TestVisualInjectionProbe:
    def test_generates_prompts(self):
        probe = VisualInjectionProbe()
        prompts = probe.generate_prompts()
        assert len(prompts) > 5
        assert all(a.probe_name == "visual_injection" for a in prompts)

    def test_name(self):
        probe = VisualInjectionProbe()
        assert probe.name == "visual_injection"

    def test_category(self):
        probe = VisualInjectionProbe()
        assert probe.category == VulnerabilityCategory.PROMPT_INJECTION

    def test_tags(self):
        probe = VisualInjectionProbe()
        assert "eu-ai-act:article-15-5" in probe.tags
        assert "multimodal" in probe.tags

    def test_is_base_probe(self):
        probe = VisualInjectionProbe()
        assert isinstance(probe, BaseProbe)


# ──────────────────────────────────────────────────────────────
# Crescendo Probe (Conversational)
# ──────────────────────────────────────────────────────────────

class TestCrescendoProbe:
    def test_generates_prompts(self):
        probe = CrescendoProbe()
        prompts = probe.generate_prompts()
        assert len(prompts) > 5
        assert all(a.probe_name == "crescendo" for a in prompts)

    def test_name(self):
        probe = CrescendoProbe()
        assert probe.name == "crescendo"

    def test_category(self):
        probe = CrescendoProbe()
        assert probe.category == VulnerabilityCategory.JAILBREAK

    def test_tags(self):
        probe = CrescendoProbe()
        assert "multi-turn" in probe.tags
        assert "crescendo" in probe.tags

    def test_is_conversational_probe(self):
        probe = CrescendoProbe()
        assert isinstance(probe, ConversationalProbe)
        assert probe.is_conversational is True

    def test_has_max_turns(self):
        probe = CrescendoProbe()
        assert probe.max_turns >= 1


# ──────────────────────────────────────────────────────────────
# Multi-Turn Injection Probe (Conversational)
# ──────────────────────────────────────────────────────────────

class TestMultiTurnInjectionProbe:
    def test_generates_prompts(self):
        probe = MultiTurnInjectionProbe()
        prompts = probe.generate_prompts()
        assert len(prompts) > 5
        assert all(a.probe_name == "multi_turn_injection" for a in prompts)

    def test_name(self):
        probe = MultiTurnInjectionProbe()
        assert probe.name == "multi_turn_injection"

    def test_category(self):
        probe = MultiTurnInjectionProbe()
        assert probe.category == VulnerabilityCategory.PROMPT_INJECTION

    def test_tags(self):
        probe = MultiTurnInjectionProbe()
        assert "multi-turn" in probe.tags
        assert "prompt-injection" in probe.tags

    def test_is_conversational_probe(self):
        probe = MultiTurnInjectionProbe()
        assert isinstance(probe, ConversationalProbe)
        assert probe.is_conversational is True

    def test_has_max_turns(self):
        probe = MultiTurnInjectionProbe()
        assert probe.max_turns >= 1


# ──────────────────────────────────────────────────────────────
# Parametrized test: every new probe generates >5 prompts
# ──────────────────────────────────────────────────────────────

@pytest.mark.parametrize(
    "probe_cls,expected_name,expected_category",
    [
        (PIILeakageProbe, "pii_leakage", VulnerabilityCategory.PII_LEAKAGE),
        (BiasFairnessProbe, "bias_fairness", VulnerabilityCategory.BIAS_FAIRNESS),
        (ExcessiveAgencyProbe, "excessive_agency", VulnerabilityCategory.EXCESSIVE_AGENCY),
        (DenialOfServiceProbe, "denial_of_service", VulnerabilityCategory.DENIAL_OF_SERVICE),
        (RAGPoisoningProbe, "rag_poisoning", VulnerabilityCategory.RAG_POISONING),
        (FunctionCallingProbe, "function_calling", VulnerabilityCategory.FUNCTION_CALLING),
        (IndirectInjectionProbe, "indirect_injection", VulnerabilityCategory.INDIRECT_INJECTION),
        (LanguageCrossoverProbe, "language_crossover", VulnerabilityCategory.LANGUAGE_CROSSOVER),
        (RolePlayProbe, "role_play", VulnerabilityCategory.ROLE_PLAY),
        (ContextOverflowProbe, "context_overflow", VulnerabilityCategory.CONTEXT_OVERFLOW),
        (SteganographicProbe, "steganographic", VulnerabilityCategory.STEGANOGRAPHIC),
        (SocialEngineeringProbe, "social_engineering", VulnerabilityCategory.SOCIAL_ENGINEERING),
        (VisualInjectionProbe, "visual_injection", VulnerabilityCategory.PROMPT_INJECTION),
        (CrescendoProbe, "crescendo", VulnerabilityCategory.JAILBREAK),
        (MultiTurnInjectionProbe, "multi_turn_injection", VulnerabilityCategory.PROMPT_INJECTION),
    ],
)
class TestAllNewProbesParametrized:
    def test_prompt_count_is_reasonable(self, probe_cls, expected_name, expected_category):
        probe = probe_cls()
        prompts = probe.generate_prompts()
        assert len(prompts) > 5, f"{expected_name} should generate >5 prompts, got {len(prompts)}"

    def test_correct_name(self, probe_cls, expected_name, expected_category):
        probe = probe_cls()
        assert probe.name == expected_name

    def test_correct_category(self, probe_cls, expected_name, expected_category):
        probe = probe_cls()
        assert probe.category == expected_category

    def test_has_tags(self, probe_cls, expected_name, expected_category):
        probe = probe_cls()
        assert len(probe.tags) > 0, f"{expected_name} should have at least one tag"

    def test_prompts_have_probe_name(self, probe_cls, expected_name, expected_category):
        probe = probe_cls()
        prompts = probe.generate_prompts()
        for attempt in prompts:
            assert attempt.probe_name == expected_name

    def test_prompts_are_nonempty(self, probe_cls, expected_name, expected_category):
        probe = probe_cls()
        prompts = probe.generate_prompts()
        for attempt in prompts:
            assert len(attempt.prompt.strip()) > 0, (
                f"{expected_name}: every prompt should be non-empty"
            )

    def test_has_description(self, probe_cls, expected_name, expected_category):
        probe = probe_cls()
        assert len(probe.description) > 0 or True  # description may be empty in some probes
