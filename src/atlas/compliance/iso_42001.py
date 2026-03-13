"""ISO/IEC 42001:2023 AI Management System (AIMS) mappings for ATLAS probe categories.

Reference: ISO/IEC 42001:2023 - Information technology -- Artificial intelligence --
Management system.

ISO 42001 specifies requirements for establishing, implementing, maintaining, and
continually improving an AI Management System (AIMS) within organizations.
"""
from __future__ import annotations

from typing import Any

# ISO 42001 Clauses and Controls mapped to ATLAS vulnerability categories.
# Clauses 4-10 define the management system requirements.
# Annex A provides reference controls.
ISO_42001: dict[str, dict[str, Any]] = {
    # ──────────────────────────────────────────────────────────
    # Clause 5: Leadership
    # ──────────────────────────────────────────────────────────
    "5.1": {
        "clause": "5",
        "title": "Leadership and Commitment",
        "description": (
            "Top management shall demonstrate leadership and commitment with "
            "respect to the AI management system, including ensuring resources, "
            "policies, and integration of AI risk management."
        ),
        "categories": [],
    },
    "5.2": {
        "clause": "5",
        "title": "AI Policy",
        "description": (
            "Top management shall establish an AI policy that includes a "
            "commitment to responsible AI, ethical use, and compliance with "
            "applicable requirements."
        ),
        "categories": [
            "toxicity",
            "harmful_content",
            "bias_fairness",
        ],
    },
    "5.3": {
        "clause": "5",
        "title": "Roles, Responsibilities, and Authorities",
        "description": (
            "Top management shall ensure that responsibilities and authorities "
            "for relevant roles are assigned and communicated within the "
            "organization for AI governance."
        ),
        "categories": ["excessive_agency"],
    },
    # ──────────────────────────────────────────────────────────
    # Clause 6: Planning
    # ──────────────────────────────────────────────────────────
    "6.1": {
        "clause": "6",
        "title": "Actions to Address Risks and Opportunities",
        "description": (
            "The organization shall determine risks and opportunities related "
            "to the AI management system and plan actions to address them, "
            "including AI-specific security and safety risks."
        ),
        "categories": [
            "prompt_injection",
            "jailbreak",
            "encoding",
            "web_injection",
            "malware",
            "denial_of_service",
        ],
    },
    "6.1.2": {
        "clause": "6",
        "title": "AI Risk Assessment",
        "description": (
            "The organization shall define and apply an AI risk assessment "
            "process that identifies risks to individuals, groups, and society "
            "from AI system deployment."
        ),
        "categories": [
            "toxicity",
            "harmful_content",
            "bias_fairness",
            "social_engineering",
            "pii_leakage",
            "data_extraction",
        ],
    },
    "6.1.3": {
        "clause": "6",
        "title": "AI Risk Treatment",
        "description": (
            "The organization shall define and apply an AI risk treatment "
            "process to select appropriate risk treatment options and determine "
            "controls necessary to implement them."
        ),
        "categories": [
            "prompt_injection",
            "jailbreak",
            "data_extraction",
            "pii_leakage",
        ],
    },
    "6.2": {
        "clause": "6",
        "title": "AI Objectives and Planning to Achieve Them",
        "description": (
            "The organization shall establish AI objectives at relevant "
            "functions and levels, including measurable safety and security "
            "targets."
        ),
        "categories": [],
    },
    # ──────────────────────────────────────────────────────────
    # Clause 7: Support
    # ──────────────────────────────────────────────────────────
    "7.1": {
        "clause": "7",
        "title": "Resources",
        "description": (
            "The organization shall determine and provide the resources needed "
            "for the establishment, implementation, maintenance, and continual "
            "improvement of the AI management system."
        ),
        "categories": [],
    },
    "7.2": {
        "clause": "7",
        "title": "Competence",
        "description": (
            "The organization shall determine the necessary competence of "
            "persons doing work that affects AI performance, safety, and security."
        ),
        "categories": [],
    },
    "7.3": {
        "clause": "7",
        "title": "Awareness",
        "description": (
            "Persons doing work under the organization's control shall be "
            "aware of the AI policy, their contribution to the AIMS, and "
            "the implications of not conforming."
        ),
        "categories": [],
    },
    "7.4": {
        "clause": "7",
        "title": "Communication",
        "description": (
            "The organization shall determine internal and external "
            "communications relevant to the AI management system, including "
            "transparency about AI system capabilities and limitations."
        ),
        "categories": ["hallucination"],
    },
    "7.5": {
        "clause": "7",
        "title": "Documented Information",
        "description": (
            "The AI management system shall include documented information "
            "required by ISO 42001 and determined by the organization as "
            "necessary for AIMS effectiveness."
        ),
        "categories": [],
    },
    # ──────────────────────────────────────────────────────────
    # Clause 8: Operation
    # ──────────────────────────────────────────────────────────
    "8.1": {
        "clause": "8",
        "title": "Operational Planning and Control",
        "description": (
            "The organization shall plan, implement, and control processes "
            "needed to meet AI management system requirements, including "
            "security controls for AI systems."
        ),
        "categories": [
            "prompt_injection",
            "jailbreak",
            "encoding",
            "web_injection",
            "indirect_injection",
            "steganographic",
            "language_crossover",
        ],
    },
    "8.2": {
        "clause": "8",
        "title": "AI Risk Assessment (Operational)",
        "description": (
            "The organization shall perform AI risk assessments at planned "
            "intervals or when significant changes are proposed or occur."
        ),
        "categories": [
            "malware",
            "denial_of_service",
            "rag_poisoning",
            "context_overflow",
        ],
    },
    "8.3": {
        "clause": "8",
        "title": "AI Risk Treatment (Operational)",
        "description": (
            "The organization shall implement the AI risk treatment plan "
            "and retain documented information on the results."
        ),
        "categories": [
            "data_extraction",
            "pii_leakage",
            "excessive_agency",
            "function_calling",
        ],
    },
    "8.4": {
        "clause": "8",
        "title": "AI System Impact Assessment",
        "description": (
            "The organization shall conduct impact assessments for AI "
            "systems, considering effects on individuals, groups, and "
            "society."
        ),
        "categories": [
            "toxicity",
            "harmful_content",
            "bias_fairness",
            "social_engineering",
            "role_play",
        ],
    },
    # ──────────────────────────────────────────────────────────
    # Clause 9: Performance Evaluation
    # ──────────────────────────────────────────────────────────
    "9.1": {
        "clause": "9",
        "title": "Monitoring, Measurement, Analysis, and Evaluation",
        "description": (
            "The organization shall determine what needs to be monitored "
            "and measured for AI systems, including security metrics, "
            "bias indicators, and performance benchmarks."
        ),
        "categories": [
            "hallucination",
            "bias_fairness",
            "toxicity",
        ],
    },
    "9.2": {
        "clause": "9",
        "title": "Internal Audit",
        "description": (
            "The organization shall conduct internal audits at planned "
            "intervals to verify the AI management system conforms to "
            "requirements and is effectively implemented."
        ),
        "categories": [
            "prompt_injection",
            "jailbreak",
            "data_extraction",
            "pii_leakage",
        ],
    },
    "9.3": {
        "clause": "9",
        "title": "Management Review",
        "description": (
            "Top management shall review the AI management system at "
            "planned intervals including security incident trends, "
            "risk assessment results, and opportunities for improvement."
        ),
        "categories": [],
    },
    # ──────────────────────────────────────────────────────────
    # Clause 10: Improvement
    # ──────────────────────────────────────────────────────────
    "10.1": {
        "clause": "10",
        "title": "Continual Improvement",
        "description": (
            "The organization shall continually improve the suitability, "
            "adequacy, and effectiveness of the AI management system."
        ),
        "categories": [],
    },
    "10.2": {
        "clause": "10",
        "title": "Nonconformity and Corrective Action",
        "description": (
            "When a nonconformity occurs (including AI safety incidents, "
            "security breaches, or bias discoveries), the organization shall "
            "react, evaluate the need for corrective action, implement changes, "
            "and review effectiveness."
        ),
        "categories": [
            "prompt_injection",
            "jailbreak",
            "data_extraction",
            "pii_leakage",
            "toxicity",
            "harmful_content",
            "bias_fairness",
            "malware",
        ],
    },
    # ──────────────────────────────────────────────────────────
    # Annex A: Reference Controls (Selected)
    # ──────────────────────────────────────────────────────────
    "A.5.3": {
        "clause": "Annex A",
        "title": "AI System Security",
        "description": (
            "Controls for securing AI systems against adversarial attacks, "
            "unauthorized access, and manipulation of inputs or outputs."
        ),
        "categories": [
            "prompt_injection",
            "jailbreak",
            "encoding",
            "web_injection",
            "indirect_injection",
            "steganographic",
            "language_crossover",
        ],
    },
    "A.5.4": {
        "clause": "Annex A",
        "title": "AI Data Quality and Protection",
        "description": (
            "Controls for ensuring the quality, integrity, and protection "
            "of data used in AI systems, including training data, input "
            "data, and output data."
        ),
        "categories": [
            "data_extraction",
            "pii_leakage",
            "rag_poisoning",
        ],
    },
    "A.6.2": {
        "clause": "Annex A",
        "title": "AI System Reliability and Robustness",
        "description": (
            "Controls for ensuring AI system outputs are reliable, robust, "
            "and resilient under various operating conditions."
        ),
        "categories": [
            "hallucination",
            "context_overflow",
            "denial_of_service",
        ],
    },
    "A.7.3": {
        "clause": "Annex A",
        "title": "Fairness and Non-Discrimination",
        "description": (
            "Controls for identifying, measuring, and mitigating bias "
            "and discrimination in AI system outputs."
        ),
        "categories": ["bias_fairness"],
    },
    "A.8.2": {
        "clause": "Annex A",
        "title": "Transparency and Explainability",
        "description": (
            "Controls for ensuring AI systems provide transparent and "
            "explainable decisions and outputs."
        ),
        "categories": ["hallucination"],
    },
    "A.9.4": {
        "clause": "Annex A",
        "title": "Human Oversight and Control",
        "description": (
            "Controls for maintaining appropriate human oversight of AI "
            "systems, including ability to override, intervene, and shut "
            "down systems."
        ),
        "categories": [
            "excessive_agency",
            "function_calling",
        ],
    },
    "A.10.1": {
        "clause": "Annex A",
        "title": "AI System Safety",
        "description": (
            "Controls for preventing AI systems from causing harm to "
            "individuals, groups, or society, including content safety "
            "and behavioral safety."
        ),
        "categories": [
            "toxicity",
            "harmful_content",
            "social_engineering",
            "malware",
            "role_play",
        ],
    },
}

# Clause titles for human-readable display
CLAUSE_TITLES: dict[str, str] = {
    "5": "Leadership",
    "6": "Planning",
    "7": "Support",
    "8": "Operation",
    "9": "Performance Evaluation",
    "10": "Improvement",
    "Annex A": "Reference Controls",
}

# Reverse mapping: category -> list of ISO 42001 clause/control IDs
CATEGORY_TO_ISO: dict[str, list[str]] = {}
for _iso_id, _info in ISO_42001.items():
    for _cat in _info["categories"]:
        CATEGORY_TO_ISO.setdefault(_cat, []).append(_iso_id)
