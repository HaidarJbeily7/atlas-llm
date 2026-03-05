"""OWASP LLM Top 10 (2025) mappings."""
from __future__ import annotations

from typing import Any

# OWASP Top 10 for LLM Applications 2025
OWASP_LLM_TOP_10: dict[str, dict[str, Any]] = {
    "LLM01": {
        "title": "Prompt Injection",
        "description": "Manipulating LLMs via crafted inputs to cause unintended actions",
        "categories": ["prompt_injection", "jailbreak", "encoding"],
    },
    "LLM02": {
        "title": "Insecure Output Handling",
        "description": "Insufficient validation of LLM outputs leading to XSS, SSRF, etc.",
        "categories": ["web_injection", "malware"],
    },
    "LLM03": {
        "title": "Training Data Poisoning",
        "description": "Manipulation of training data to introduce vulnerabilities",
        "categories": [],  # Not directly testable via probes
    },
    "LLM04": {
        "title": "Model Denial of Service",
        "description": "Resource-intensive operations causing service degradation",
        "categories": [],  # Requires different testing approach
    },
    "LLM05": {
        "title": "Supply Chain Vulnerabilities",
        "description": "Vulnerabilities in LLM supply chain components",
        "categories": [],
    },
    "LLM06": {
        "title": "Sensitive Information Disclosure",
        "description": "Leakage of confidential data through LLM outputs",
        "categories": ["data_extraction"],
    },
    "LLM07": {
        "title": "Insecure Plugin Design",
        "description": "Insecure plugin interactions and trust boundaries",
        "categories": [],
    },
    "LLM08": {
        "title": "Excessive Agency",
        "description": "Granting LLMs excessive functionality or autonomy",
        "categories": [],
    },
    "LLM09": {
        "title": "Overreliance",
        "description": "Overreliance on LLM outputs without verification",
        "categories": ["hallucination"],
    },
    "LLM10": {
        "title": "Model Theft",
        "description": "Unauthorized access or extraction of LLM models",
        "categories": ["data_extraction"],
    },
}

# Reverse mapping: category -> OWASP IDs
CATEGORY_TO_OWASP: dict[str, list[str]] = {}
for owasp_id, info in OWASP_LLM_TOP_10.items():
    for cat in info["categories"]:
        CATEGORY_TO_OWASP.setdefault(cat, []).append(owasp_id)
