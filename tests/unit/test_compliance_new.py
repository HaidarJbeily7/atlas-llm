"""Tests for new compliance frameworks (NIST AI RMF, ISO 42001, updated OWASP/EU AI Act)."""
import pytest

from atlas.compliance.mapper import ComplianceMapper
from atlas.compliance.nist_ai_rmf import NIST_AI_RMF, CATEGORY_TO_NIST
from atlas.compliance.iso_42001 import ISO_42001, CATEGORY_TO_ISO, CLAUSE_TITLES
from atlas.compliance.owasp_llm import OWASP_LLM_TOP_10, CATEGORY_TO_OWASP
from atlas.compliance.eu_ai_act import EU_AI_ACT_MAPPING, ARTICLE_TITLES


# ──────────────────────────────────────────────────────────────
# NIST AI RMF
# ──────────────────────────────────────────────────────────────

class TestNISTAIRMF:
    def test_nist_mapping_exists(self):
        assert len(NIST_AI_RMF) > 0

    def test_nist_has_entries(self):
        assert len(NIST_AI_RMF) >= 10

    def test_nist_has_all_four_functions(self):
        functions = {info["function"] for info in NIST_AI_RMF.values()}
        assert "GOVERN" in functions
        assert "MAP" in functions
        assert "MEASURE" in functions
        assert "MANAGE" in functions

    def test_nist_entries_have_required_fields(self):
        for nist_id, info in NIST_AI_RMF.items():
            assert "function" in info, f"{nist_id} missing 'function'"
            assert "title" in info, f"{nist_id} missing 'title'"
            assert "description" in info, f"{nist_id} missing 'description'"
            assert "categories" in info, f"{nist_id} missing 'categories'"
            assert isinstance(info["categories"], list)

    def test_category_to_nist_reverse_mapping_exists(self):
        assert len(CATEGORY_TO_NIST) > 0

    def test_category_to_nist_has_key_categories(self):
        assert "prompt_injection" in CATEGORY_TO_NIST
        assert "jailbreak" in CATEGORY_TO_NIST
        assert "pii_leakage" in CATEGORY_TO_NIST
        assert "bias_fairness" in CATEGORY_TO_NIST

    def test_nist_prompt_injection_maps_to_measure_and_manage(self):
        nist_ids = CATEGORY_TO_NIST.get("prompt_injection", [])
        assert len(nist_ids) > 0
        functions = {NIST_AI_RMF[nid]["function"] for nid in nist_ids}
        assert "MEASURE" in functions or "MANAGE" in functions


class TestNISTMapperIntegration:
    def test_get_nist_for_category_returns_list(self):
        mapper = ComplianceMapper()
        result = mapper.get_nist_for_category("prompt_injection")
        assert isinstance(result, list)
        assert len(result) > 0

    def test_get_nist_for_unknown_category(self):
        mapper = ComplianceMapper()
        result = mapper.get_nist_for_category("nonexistent_category")
        assert result == []

    def test_get_nist_title(self):
        mapper = ComplianceMapper()
        title = mapper.get_nist_title("MEASURE 2.6")
        assert "Security" in title or "Resilience" in title

    def test_get_nist_function(self):
        mapper = ComplianceMapper()
        function = mapper.get_nist_function("MANAGE 2.3")
        assert function == "MANAGE"

    def test_nist_for_bias_fairness(self):
        mapper = ComplianceMapper()
        nist_ids = mapper.get_nist_for_category("bias_fairness")
        assert len(nist_ids) > 0

    def test_nist_for_hallucination(self):
        mapper = ComplianceMapper()
        nist_ids = mapper.get_nist_for_category("hallucination")
        assert len(nist_ids) > 0

    def test_nist_for_denial_of_service(self):
        mapper = ComplianceMapper()
        nist_ids = mapper.get_nist_for_category("denial_of_service")
        assert len(nist_ids) > 0


# ──────────────────────────────────────────────────────────────
# ISO 42001
# ──────────────────────────────────────────────────────────────

class TestISO42001:
    def test_iso_mapping_exists(self):
        assert len(ISO_42001) > 0

    def test_iso_has_entries(self):
        assert len(ISO_42001) >= 10

    def test_iso_entries_have_required_fields(self):
        for iso_id, info in ISO_42001.items():
            assert "clause" in info, f"{iso_id} missing 'clause'"
            assert "title" in info, f"{iso_id} missing 'title'"
            assert "description" in info, f"{iso_id} missing 'description'"
            assert "categories" in info, f"{iso_id} missing 'categories'"
            assert isinstance(info["categories"], list)

    def test_iso_covers_multiple_clauses(self):
        clauses = {info["clause"] for info in ISO_42001.values()}
        # Should cover clauses 5 through 10 and Annex A at minimum
        assert len(clauses) >= 4

    def test_iso_has_annex_a_controls(self):
        annex_a_ids = [k for k in ISO_42001 if k.startswith("A.")]
        assert len(annex_a_ids) > 0

    def test_category_to_iso_reverse_mapping_exists(self):
        assert len(CATEGORY_TO_ISO) > 0

    def test_category_to_iso_has_key_categories(self):
        assert "prompt_injection" in CATEGORY_TO_ISO
        assert "bias_fairness" in CATEGORY_TO_ISO
        assert "pii_leakage" in CATEGORY_TO_ISO
        assert "excessive_agency" in CATEGORY_TO_ISO

    def test_clause_titles_exist(self):
        assert len(CLAUSE_TITLES) > 0
        assert "5" in CLAUSE_TITLES or "6" in CLAUSE_TITLES


class TestISOMapperIntegration:
    def test_get_iso_for_category_returns_list(self):
        mapper = ComplianceMapper()
        result = mapper.get_iso_for_category("prompt_injection")
        assert isinstance(result, list)
        assert len(result) > 0

    def test_get_iso_for_unknown_category(self):
        mapper = ComplianceMapper()
        result = mapper.get_iso_for_category("nonexistent_category")
        assert result == []

    def test_get_iso_title(self):
        mapper = ComplianceMapper()
        title = mapper.get_iso_title("6.1")
        assert len(title) > 0

    def test_get_iso_clause_title(self):
        mapper = ComplianceMapper()
        title = mapper.get_iso_clause_title("6")
        assert title == "Planning"

    def test_iso_for_toxicity(self):
        mapper = ComplianceMapper()
        iso_ids = mapper.get_iso_for_category("toxicity")
        assert len(iso_ids) > 0

    def test_iso_for_function_calling(self):
        mapper = ComplianceMapper()
        iso_ids = mapper.get_iso_for_category("function_calling")
        assert len(iso_ids) > 0

    def test_iso_for_social_engineering(self):
        mapper = ComplianceMapper()
        iso_ids = mapper.get_iso_for_category("social_engineering")
        assert len(iso_ids) > 0


# ──────────────────────────────────────────────────────────────
# OWASP Updated Categories
# ──────────────────────────────────────────────────────────────

class TestOWASPUpdatedCategories:
    def test_owasp_has_10_entries(self):
        assert len(OWASP_LLM_TOP_10) == 10

    def test_llm03_has_rag_poisoning(self):
        categories = OWASP_LLM_TOP_10["LLM03"]["categories"]
        assert "rag_poisoning" in categories

    def test_llm04_has_denial_of_service(self):
        categories = OWASP_LLM_TOP_10["LLM04"]["categories"]
        assert "denial_of_service" in categories

    def test_llm04_has_context_overflow(self):
        categories = OWASP_LLM_TOP_10["LLM04"]["categories"]
        assert "context_overflow" in categories

    def test_llm07_has_function_calling(self):
        categories = OWASP_LLM_TOP_10["LLM07"]["categories"]
        assert "function_calling" in categories

    def test_llm08_has_excessive_agency(self):
        categories = OWASP_LLM_TOP_10["LLM08"]["categories"]
        assert "excessive_agency" in categories

    def test_llm08_has_function_calling(self):
        categories = OWASP_LLM_TOP_10["LLM08"]["categories"]
        assert "function_calling" in categories

    def test_llm01_has_new_injection_categories(self):
        categories = OWASP_LLM_TOP_10["LLM01"]["categories"]
        assert "indirect_injection" in categories
        assert "context_overflow" in categories
        assert "steganographic" in categories
        assert "language_crossover" in categories
        assert "role_play" in categories

    def test_llm06_has_pii_leakage(self):
        categories = OWASP_LLM_TOP_10["LLM06"]["categories"]
        assert "pii_leakage" in categories

    def test_reverse_mapping_new_categories(self):
        assert "rag_poisoning" in CATEGORY_TO_OWASP
        assert "denial_of_service" in CATEGORY_TO_OWASP
        assert "function_calling" in CATEGORY_TO_OWASP
        assert "excessive_agency" in CATEGORY_TO_OWASP
        assert "indirect_injection" in CATEGORY_TO_OWASP
        assert "pii_leakage" in CATEGORY_TO_OWASP


# ──────────────────────────────────────────────────────────────
# EU AI Act New Category Mappings
# ──────────────────────────────────────────────────────────────

class TestEUAIActNewCategories:
    def test_pii_leakage_mapped(self):
        assert "pii_leakage" in EU_AI_ACT_MAPPING
        assert len(EU_AI_ACT_MAPPING["pii_leakage"]["articles"]) > 0

    def test_bias_fairness_mapped(self):
        assert "bias_fairness" in EU_AI_ACT_MAPPING
        articles = EU_AI_ACT_MAPPING["bias_fairness"]["articles"]
        assert "article-10-2-f" in articles

    def test_excessive_agency_mapped(self):
        assert "excessive_agency" in EU_AI_ACT_MAPPING
        articles = EU_AI_ACT_MAPPING["excessive_agency"]["articles"]
        assert "article-14" in articles

    def test_denial_of_service_mapped(self):
        assert "denial_of_service" in EU_AI_ACT_MAPPING
        assert "article-15-5" in EU_AI_ACT_MAPPING["denial_of_service"]["articles"]

    def test_rag_poisoning_mapped(self):
        assert "rag_poisoning" in EU_AI_ACT_MAPPING
        assert "article-10" in EU_AI_ACT_MAPPING["rag_poisoning"]["articles"]

    def test_function_calling_mapped(self):
        assert "function_calling" in EU_AI_ACT_MAPPING
        articles = EU_AI_ACT_MAPPING["function_calling"]["articles"]
        assert "article-15-5" in articles
        assert "article-14" in articles

    def test_indirect_injection_mapped(self):
        assert "indirect_injection" in EU_AI_ACT_MAPPING
        assert "article-15-5" in EU_AI_ACT_MAPPING["indirect_injection"]["articles"]

    def test_language_crossover_mapped(self):
        assert "language_crossover" in EU_AI_ACT_MAPPING

    def test_role_play_mapped(self):
        assert "role_play" in EU_AI_ACT_MAPPING

    def test_context_overflow_mapped(self):
        assert "context_overflow" in EU_AI_ACT_MAPPING

    def test_steganographic_mapped(self):
        assert "steganographic" in EU_AI_ACT_MAPPING

    def test_social_engineering_mapped(self):
        assert "social_engineering" in EU_AI_ACT_MAPPING
        articles = EU_AI_ACT_MAPPING["social_engineering"]["articles"]
        assert "article-9" in articles

    def test_all_new_categories_have_requirement(self):
        new_categories = [
            "pii_leakage", "bias_fairness", "excessive_agency",
            "denial_of_service", "rag_poisoning", "function_calling",
            "indirect_injection", "language_crossover", "role_play",
            "context_overflow", "steganographic", "social_engineering",
        ]
        for cat in new_categories:
            assert cat in EU_AI_ACT_MAPPING, f"{cat} not in EU_AI_ACT_MAPPING"
            mapping = EU_AI_ACT_MAPPING[cat]
            assert "requirement" in mapping, f"{cat} missing requirement"
            assert len(mapping["requirement"]) > 0

    def test_article_titles_cover_referenced_articles(self):
        """All articles referenced in mappings should have titles."""
        all_articles = set()
        for mapping in EU_AI_ACT_MAPPING.values():
            all_articles.update(mapping.get("articles", []))
        for article in all_articles:
            assert article in ARTICLE_TITLES, f"Missing title for {article}"


# ──────────────────────────────────────────────────────────────
# ComplianceMapper aggregation tests
# ──────────────────────────────────────────────────────────────

class TestComplianceMapperAggregation:
    def test_get_all_mappings_includes_all_frameworks(self):
        mapper = ComplianceMapper()
        mappings = mapper.get_all_mappings_for_category("prompt_injection")
        assert "eu_ai_act" in mappings
        assert "owasp_llm" in mappings
        assert "nist_ai_rmf" in mappings
        assert "iso_42001" in mappings

    def test_full_compliance_map_includes_new_categories(self):
        mapper = ComplianceMapper()
        full = mapper.get_full_compliance_map()
        assert "pii_leakage" in full
        assert "bias_fairness" in full
        assert "function_calling" in full
        assert "rag_poisoning" in full

    def test_full_compliance_map_has_all_four_frameworks_per_category(self):
        mapper = ComplianceMapper()
        full = mapper.get_full_compliance_map()
        for cat, mappings in full.items():
            assert "eu_ai_act" in mappings, f"{cat} missing eu_ai_act"
            assert "owasp_llm" in mappings, f"{cat} missing owasp_llm"
            assert "nist_ai_rmf" in mappings, f"{cat} missing nist_ai_rmf"
            assert "iso_42001" in mappings, f"{cat} missing iso_42001"
