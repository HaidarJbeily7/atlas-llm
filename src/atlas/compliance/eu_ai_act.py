"""EU AI Act article mappings for ATLAS probe categories."""
from __future__ import annotations

from typing import Any

# Mapping of probe categories to EU AI Act requirements
# Based on COMPL-AI Framework (ETH Zurich, INSAIT, LatticeFlow AI)
# arXiv:2410.07959 - https://arxiv.org/abs/2410.07959
EU_AI_ACT_MAPPING: dict[str, dict[str, Any]] = {
    "prompt_injection": {
        "articles": ["article-15-5"],
        "requirement": "Cyberattack Resilience",
        "description": "Resilience against adversarial input manipulation (Art. 15(5))",
        "risk_level": "high",
    },
    "jailbreak": {
        "articles": ["article-15-5", "article-55-1-d"],
        "requirement": "Cyberattack Resilience",
        "description": "Resistance to safety measure circumvention (Art. 15(5), Art. 55(1)(d))",
        "risk_level": "high",
    },
    "encoding": {
        "articles": ["article-15-5"],
        "requirement": "Cyberattack Resilience",
        "description": "Resistance to encoding-based evasion attacks (Art. 15(5))",
        "risk_level": "high",
    },
    "data_extraction": {
        "articles": ["article-10", "article-53-1-c"],
        "requirement": "User Privacy Protection / No Copyright Infringement",
        "description": "Prevention of unauthorized data disclosure (Art. 10, Art. 53(1)(c))",
        "risk_level": "high",
    },
    "toxicity": {
        "articles": ["article-9", "article-95"],
        "requirement": "Harmful Content Prevention",
        "description": "Prevention of toxic/harmful content generation (Art. 9, Art. 95)",
        "risk_level": "high",
    },
    "hallucination": {
        "articles": ["article-13-1", "article-15-1"],
        "requirement": "Accuracy / Interpretability",
        "description": "Factual accuracy and reliability evaluation (Art. 13(1), Art. 15(1))",
        "risk_level": "limited",
    },
    "web_injection": {
        "articles": ["article-15-5"],
        "requirement": "Cyberattack Resilience",
        "description": "Web injection and output manipulation resistance (Art. 15(5))",
        "risk_level": "high",
    },
    "malware": {
        "articles": ["article-15-5"],
        "requirement": "Cyberattack Resilience",
        "description": "Resistance to malware/exploit code generation (Art. 15(5))",
        "risk_level": "high",
    },
}

# COMPL-AI Technical Requirements (Academic Reference)
COMPL_AI_REQUIREMENTS: dict[str, dict[str, Any]] = {
    "cyberattack_resilience": {
        "articles": ["article-15-5", "article-55-1-d"],
        "principle": "Technical Robustness & Safety",
        "description": "Resistance to jailbreaks, prompt injection, and adversarial manipulation per Art. 15(5)",
        "benchmarks": ["instruction_goal_hijacking", "llm_rules", "dan_jailbreaks"],
    },
    "robustness_predictability": {
        "articles": ["article-15-1", "article-15-4"],
        "principle": "Technical Robustness & Safety",
        "description": "Consistent responses under input variations per Art. 15(4)",
        "benchmarks": ["boolq_contrast", "mmlu_pro_robustness"],
    },
    "corrigibility": {
        "articles": ["article-15", "article-14"],
        "principle": "Technical Robustness & Safety",
        "description": "Ability to be corrected and controlled per Art. 14 and Art. 15",
        "benchmarks": ["corrigibility_tests"],
    },
    "training_data_suitability": {
        "articles": ["article-10-2", "article-10-3"],
        "principle": "Privacy & Data Governance",
        "description": "Appropriate data quality and relevance per Art. 10(2-3)",
        "benchmarks": ["data_quality_assessment"],
    },
    "no_copyright_infringement": {
        "articles": ["article-53-1-c", "article-53-1-d"],
        "principle": "Privacy & Data Governance",
        "description": "Protection of copyrighted training data per Art. 53(1)(c)",
        "benchmarks": ["copyright_memorization", "training_data_extraction"],
    },
    "user_privacy_protection": {
        "articles": ["article-10-5", "article-53-1-e"],
        "principle": "Privacy & Data Governance",
        "description": "Protection of user data and privacy per Art. 10(5)",
        "benchmarks": ["pii_leakage", "privacy_violation"],
    },
    "capabilities_limitations": {
        "articles": ["article-13-1", "article-53-1-a"],
        "principle": "Transparency",
        "description": "Clear documentation of model capabilities per Art. 13(1)",
        "benchmarks": ["capability_documentation"],
    },
    "interpretability": {
        "articles": ["article-13-1", "article-14-4"],
        "principle": "Transparency",
        "description": "Understandable model behavior per Art. 14(4)",
        "benchmarks": ["interpretability_tests"],
    },
    "ai_disclosure": {
        "articles": ["article-50-1", "article-50-2"],
        "principle": "Transparency",
        "description": "Disclosure of AI-generated content per Art. 50",
        "benchmarks": ["ai_disclosure_compliance"],
    },
    "absence_of_bias": {
        "articles": ["article-10-2-f", "annex-iv-2-g"],
        "principle": "Diversity, Non-discrimination & Fairness",
        "description": "Freedom from systematic bias per Art. 10(2)(f) and Annex IV",
        "benchmarks": ["bias_detection", "demographic_parity"],
    },
    "absence_of_discrimination": {
        "articles": ["article-15-4", "article-10-2-g"],
        "principle": "Diversity, Non-discrimination & Fairness",
        "description": "Non-discriminatory outputs per Art. 15(4)",
        "benchmarks": ["discrimination_testing", "fairness_assessment"],
    },
    "harmful_content_prevention": {
        "articles": ["article-9", "article-95"],
        "principle": "Social & Environmental Well-being",
        "description": "Prevention of toxic/harmful outputs per Art. 9 and Art. 95",
        "benchmarks": ["toxicity_generation", "harmful_content"],
    },
}

# Article ID to human-readable title mapping
ARTICLE_TITLES: dict[str, str] = {
    "article-9": "Risk Management System",
    "article-10": "Data and Data Governance",
    "article-10-2": "Data Quality Requirements",
    "article-10-2-f": "Bias Examination in Training Data",
    "article-10-3": "Data Representativeness",
    "article-10-5": "Privacy and Data Protection",
    "article-13": "Transparency and Information",
    "article-13-1": "Transparent Operation",
    "article-14": "Human Oversight",
    "article-14-4": "Interpretability for Users",
    "article-15": "Accuracy, Robustness, Cybersecurity",
    "article-15-1": "Accuracy and Reliability",
    "article-15-4": "Robustness and Non-discrimination",
    "article-15-5": "Cyberattack Resilience",
    "article-40": "Harmonised Standards",
    "article-50": "AI System Transparency",
    "article-50-1": "AI Interaction Disclosure",
    "article-50-2": "Content Marking",
    "article-53-1-a": "Model Capability Documentation",
    "article-53-1-c": "Training Data Summary",
    "article-53-1-d": "Copyright Policy",
    "article-53-1-e": "Privacy Compliance",
    "article-55-1-d": "Adversarial Testing Requirements",
    "article-95": "Societal Well-being",
    "annex-iv": "Technical Documentation",
    "annex-iv-2-g": "Bias Metrics",
}
