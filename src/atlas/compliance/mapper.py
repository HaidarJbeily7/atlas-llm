"""Compliance mapping between probe categories and regulatory frameworks."""
from __future__ import annotations

from typing import Any

from atlas.compliance.eu_ai_act import ARTICLE_TITLES, EU_AI_ACT_MAPPING
from atlas.compliance.owasp_llm import CATEGORY_TO_OWASP, OWASP_LLM_TOP_10


class ComplianceMapper:
    """Maps probe categories to EU AI Act articles and OWASP LLM Top 10."""

    def get_articles_for_category(self, category: str) -> list[str]:
        """Get EU AI Act articles relevant to a vulnerability category."""
        mapping = EU_AI_ACT_MAPPING.get(category, {})
        return mapping.get("articles", [])

    def get_owasp_for_category(self, category: str) -> list[str]:
        """Get OWASP LLM Top 10 IDs relevant to a vulnerability category."""
        return CATEGORY_TO_OWASP.get(category, [])

    def get_article_title(self, article_id: str) -> str:
        """Get human-readable title for an EU AI Act article."""
        return ARTICLE_TITLES.get(article_id, article_id)

    def get_requirement_for_category(self, category: str) -> str:
        """Get the EU AI Act requirement name for a category."""
        mapping = EU_AI_ACT_MAPPING.get(category, {})
        return mapping.get("requirement", "Unknown")

    def get_all_mappings_for_category(self, category: str) -> dict[str, Any]:
        """Get all compliance mappings for a vulnerability category."""
        eu_mapping = EU_AI_ACT_MAPPING.get(category, {})
        owasp_ids = CATEGORY_TO_OWASP.get(category, [])

        return {
            "eu_ai_act": {
                "articles": eu_mapping.get("articles", []),
                "requirement": eu_mapping.get("requirement", ""),
                "description": eu_mapping.get("description", ""),
                "risk_level": eu_mapping.get("risk_level", ""),
            },
            "owasp_llm": {
                "ids": owasp_ids,
                "details": [
                    {"id": oid, **OWASP_LLM_TOP_10[oid]}
                    for oid in owasp_ids
                    if oid in OWASP_LLM_TOP_10
                ],
            },
        }

    def get_full_compliance_map(self) -> dict[str, dict[str, Any]]:
        """Get complete mapping for all categories."""
        all_categories = set(EU_AI_ACT_MAPPING.keys()) | set(CATEGORY_TO_OWASP.keys())
        return {cat: self.get_all_mappings_for_category(cat) for cat in sorted(all_categories)}
