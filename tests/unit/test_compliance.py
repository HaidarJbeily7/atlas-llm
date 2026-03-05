"""Tests for compliance mapping."""
from atlas.compliance.mapper import ComplianceMapper
from atlas.compliance.eu_ai_act import EU_AI_ACT_MAPPING, ARTICLE_TITLES
from atlas.compliance.owasp_llm import OWASP_LLM_TOP_10, CATEGORY_TO_OWASP


class TestComplianceMapper:
    def test_get_articles_for_prompt_injection(self):
        mapper = ComplianceMapper()
        articles = mapper.get_articles_for_category("prompt_injection")
        assert "article-15-5" in articles

    def test_get_owasp_for_jailbreak(self):
        mapper = ComplianceMapper()
        owasp = mapper.get_owasp_for_category("jailbreak")
        assert "LLM01" in owasp

    def test_get_article_title(self):
        mapper = ComplianceMapper()
        title = mapper.get_article_title("article-15-5")
        assert "Cyberattack" in title

    def test_get_all_mappings(self):
        mapper = ComplianceMapper()
        mappings = mapper.get_all_mappings_for_category("toxicity")
        assert "eu_ai_act" in mappings
        assert "owasp_llm" in mappings

    def test_full_compliance_map(self):
        mapper = ComplianceMapper()
        full = mapper.get_full_compliance_map()
        assert len(full) > 0


class TestEUAIActMapping:
    def test_all_categories_mapped(self):
        expected = ["prompt_injection", "jailbreak", "encoding", "data_extraction",
                    "toxicity", "hallucination", "web_injection", "malware"]
        for cat in expected:
            assert cat in EU_AI_ACT_MAPPING


class TestOWASP:
    def test_all_10_entries(self):
        assert len(OWASP_LLM_TOP_10) == 10
        for i in range(1, 11):
            assert f"LLM{i:02d}" in OWASP_LLM_TOP_10
