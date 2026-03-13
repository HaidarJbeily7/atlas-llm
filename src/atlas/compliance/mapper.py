"""Compliance mapping between probe categories and regulatory frameworks."""
from __future__ import annotations

from typing import Any

from atlas.compliance.eu_ai_act import ARTICLE_TITLES, EU_AI_ACT_MAPPING
from atlas.compliance.iso_42001 import CATEGORY_TO_ISO, CLAUSE_TITLES, ISO_42001
from atlas.compliance.nist_ai_rmf import CATEGORY_TO_NIST, NIST_AI_RMF
from atlas.compliance.owasp_llm import CATEGORY_TO_OWASP, OWASP_LLM_TOP_10


class ComplianceMapper:
    """Maps probe categories to EU AI Act articles, OWASP LLM Top 10,
    NIST AI RMF subcategories, and ISO 42001 clauses."""

    # ── EU AI Act ─────────────────────────────────────────────

    def get_articles_for_category(self, category: str) -> list[str]:
        """Get EU AI Act articles relevant to a vulnerability category."""
        mapping = EU_AI_ACT_MAPPING.get(category, {})
        return mapping.get("articles", [])

    def get_article_title(self, article_id: str) -> str:
        """Get human-readable title for an EU AI Act article."""
        return ARTICLE_TITLES.get(article_id, article_id)

    def get_requirement_for_category(self, category: str) -> str:
        """Get the EU AI Act requirement name for a category."""
        mapping = EU_AI_ACT_MAPPING.get(category, {})
        return mapping.get("requirement", "Unknown")

    # ── OWASP LLM Top 10 ─────────────────────────────────────

    def get_owasp_for_category(self, category: str) -> list[str]:
        """Get OWASP LLM Top 10 IDs relevant to a vulnerability category."""
        return CATEGORY_TO_OWASP.get(category, [])

    # ── NIST AI RMF ───────────────────────────────────────────

    def get_nist_for_category(self, category: str) -> list[str]:
        """Get NIST AI RMF subcategory IDs relevant to a vulnerability category.

        Returns a list of subcategory identifiers (e.g. ``["MANAGE 2.3", "MEASURE 2.6"]``).
        """
        return CATEGORY_TO_NIST.get(category, [])

    def get_nist_title(self, nist_id: str) -> str:
        """Get human-readable title for a NIST AI RMF subcategory."""
        entry = NIST_AI_RMF.get(nist_id, {})
        return entry.get("title", nist_id)

    def get_nist_function(self, nist_id: str) -> str:
        """Get the NIST AI RMF function (GOVERN/MAP/MEASURE/MANAGE) for a subcategory."""
        entry = NIST_AI_RMF.get(nist_id, {})
        return entry.get("function", "Unknown")

    # ── ISO 42001 ─────────────────────────────────────────────

    def get_iso_for_category(self, category: str) -> list[str]:
        """Get ISO 42001 clause/control IDs relevant to a vulnerability category.

        Returns a list of clause identifiers (e.g. ``["6.1", "8.1", "A.5.3"]``).
        """
        return CATEGORY_TO_ISO.get(category, [])

    def get_iso_title(self, iso_id: str) -> str:
        """Get human-readable title for an ISO 42001 clause or control."""
        entry = ISO_42001.get(iso_id, {})
        return entry.get("title", iso_id)

    def get_iso_clause_title(self, clause: str) -> str:
        """Get human-readable title for a top-level ISO 42001 clause number."""
        return CLAUSE_TITLES.get(clause, clause)

    # ── Aggregated Mappings ───────────────────────────────────

    def get_all_mappings_for_category(self, category: str) -> dict[str, Any]:
        """Get all compliance mappings for a vulnerability category."""
        eu_mapping = EU_AI_ACT_MAPPING.get(category, {})
        owasp_ids = CATEGORY_TO_OWASP.get(category, [])
        nist_ids = CATEGORY_TO_NIST.get(category, [])
        iso_ids = CATEGORY_TO_ISO.get(category, [])

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
            "nist_ai_rmf": {
                "ids": nist_ids,
                "details": [
                    {
                        "id": nid,
                        "function": NIST_AI_RMF[nid]["function"],
                        "title": NIST_AI_RMF[nid]["title"],
                        "description": NIST_AI_RMF[nid]["description"],
                    }
                    for nid in nist_ids
                    if nid in NIST_AI_RMF
                ],
            },
            "iso_42001": {
                "ids": iso_ids,
                "details": [
                    {
                        "id": iid,
                        "clause": ISO_42001[iid]["clause"],
                        "title": ISO_42001[iid]["title"],
                        "description": ISO_42001[iid]["description"],
                    }
                    for iid in iso_ids
                    if iid in ISO_42001
                ],
            },
        }

    def get_full_compliance_map(self) -> dict[str, dict[str, Any]]:
        """Get complete mapping for all categories."""
        all_categories = (
            set(EU_AI_ACT_MAPPING.keys())
            | set(CATEGORY_TO_OWASP.keys())
            | set(CATEGORY_TO_NIST.keys())
            | set(CATEGORY_TO_ISO.keys())
        )
        return {
            cat: self.get_all_mappings_for_category(cat)
            for cat in sorted(all_categories)
        }
