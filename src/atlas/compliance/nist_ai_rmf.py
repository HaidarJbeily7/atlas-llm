"""NIST AI Risk Management Framework (AI RMF 1.0) mappings for ATLAS probe categories.

Reference: https://www.nist.gov/itl/ai-risk-management-framework
The NIST AI RMF provides a structured approach to managing AI risks across
four core functions: GOVERN, MAP, MEASURE, and MANAGE.
"""
from __future__ import annotations

from typing import Any

# NIST AI RMF Functions and Subcategories
# Each function contains subcategories with their descriptions and related ATLAS categories.
NIST_AI_RMF: dict[str, dict[str, Any]] = {
    # ──────────────────────────────────────────────────────────
    # GOVERN: Policies, processes, procedures, and practices
    # ──────────────────────────────────────────────────────────
    "GOVERN 1.1": {
        "function": "GOVERN",
        "title": "Legal and Regulatory Requirements",
        "description": (
            "Legal and regulatory requirements involving AI are understood, "
            "managed, and documented."
        ),
        "categories": [],
    },
    "GOVERN 1.2": {
        "function": "GOVERN",
        "title": "Trustworthy AI Characteristics",
        "description": (
            "The characteristics of trustworthy AI are integrated into "
            "organizational policies, processes, and procedures."
        ),
        "categories": [],
    },
    "GOVERN 1.3": {
        "function": "GOVERN",
        "title": "Organizational AI Risk Management Processes",
        "description": (
            "Processes and procedures are in place to determine whether and how "
            "to deploy an AI system. Risk tolerance and management are established."
        ),
        "categories": ["toxicity", "harmful_content", "social_engineering"],
    },
    "GOVERN 1.4": {
        "function": "GOVERN",
        "title": "Risk Management Process Integration",
        "description": (
            "The risk management process and its outcomes are established "
            "through transparent policies and other controls."
        ),
        "categories": [],
    },
    "GOVERN 1.5": {
        "function": "GOVERN",
        "title": "Organizational AI Risk Governance",
        "description": (
            "Ongoing monitoring and periodic review of AI risk management "
            "processes and their outcomes are planned and organizational roles "
            "and responsibilities are clearly defined."
        ),
        "categories": [],
    },
    "GOVERN 1.6": {
        "function": "GOVERN",
        "title": "AI Workforce Diversity and Competency",
        "description": (
            "Competency, awareness, and training programs address AI risks "
            "and responsible AI practices."
        ),
        "categories": ["bias_fairness"],
    },
    "GOVERN 1.7": {
        "function": "GOVERN",
        "title": "Data Governance and Privacy",
        "description": (
            "Processes and procedures are in place for de-identification, "
            "data protection, and privacy. Data provenance and lineage are "
            "maintained."
        ),
        "categories": [
            "data_extraction",
            "pii_leakage",
        ],
    },
    # ──────────────────────────────────────────────────────────
    # MAP: Contextualize risks relating to an AI system
    # ──────────────────────────────────────────────────────────
    "MAP 1.1": {
        "function": "MAP",
        "title": "Intended Purpose and Context",
        "description": (
            "Intended purposes, potentially beneficial uses, context of use, "
            "and known limitations are documented."
        ),
        "categories": ["excessive_agency"],
    },
    "MAP 1.5": {
        "function": "MAP",
        "title": "Organizational Risk Tolerances",
        "description": (
            "Organizational risk tolerances are established and applied "
            "to the AI system's context of use."
        ),
        "categories": [],
    },
    "MAP 2.1": {
        "function": "MAP",
        "title": "User Interaction and AI System Categorization",
        "description": (
            "The specific task, type of user interaction, and methods for "
            "human-AI teaming are defined and documented."
        ),
        "categories": ["role_play"],
    },
    "MAP 2.2": {
        "function": "MAP",
        "title": "Interdependencies and External Factors",
        "description": (
            "Scientific integrity and TEVV (Test, Evaluation, Verification, "
            "and Validation) are applied for AI system components and upstream "
            "third-party entities."
        ),
        "categories": ["rag_poisoning", "indirect_injection"],
    },
    "MAP 2.3": {
        "function": "MAP",
        "title": "Bias Identification and Assessment",
        "description": (
            "AI system performance and trustworthiness characteristics "
            "are identified, measured, and evaluated. AI system performance "
            "is monitored for bias, discrimination, and other trustworthiness "
            "concerns."
        ),
        "categories": ["bias_fairness"],
    },
    "MAP 3.1": {
        "function": "MAP",
        "title": "Benefits and Costs Assessment",
        "description": (
            "Potential benefits and costs, including impacts on individuals, "
            "communities, and the environment, are assessed."
        ),
        "categories": [],
    },
    "MAP 3.5": {
        "function": "MAP",
        "title": "Likelihood and Impact Assessment",
        "description": (
            "Likelihood and severity of identified AI risks are estimated "
            "and used to prioritize responses."
        ),
        "categories": [],
    },
    # ──────────────────────────────────────────────────────────
    # MEASURE: Analyze, assess, and track AI risks
    # ──────────────────────────────────────────────────────────
    "MEASURE 1.1": {
        "function": "MEASURE",
        "title": "Appropriate Methods and Metrics",
        "description": (
            "Appropriate methods and metrics are identified and applied "
            "to evaluate AI system trustworthiness."
        ),
        "categories": [],
    },
    "MEASURE 2.2": {
        "function": "MEASURE",
        "title": "Evaluations for Reliability and Robustness",
        "description": (
            "Evaluations involving AI system reliability, robustness, "
            "and resilience are planned and results documented."
        ),
        "categories": [
            "hallucination",
            "context_overflow",
            "denial_of_service",
        ],
    },
    "MEASURE 2.3": {
        "function": "MEASURE",
        "title": "AI System Performance and Trustworthiness",
        "description": (
            "AI system performance and trustworthiness characteristics "
            "are measurable and regularly evaluated."
        ),
        "categories": [],
    },
    "MEASURE 2.5": {
        "function": "MEASURE",
        "title": "AI System Accuracy and Validity",
        "description": (
            "The AI system's output accuracy, validity, and reliability "
            "are measured and documented."
        ),
        "categories": ["hallucination"],
    },
    "MEASURE 2.6": {
        "function": "MEASURE",
        "title": "AI System Security and Resilience",
        "description": (
            "The AI system is evaluated for security risks including "
            "adversarial attacks, data poisoning, and prompt manipulation."
        ),
        "categories": [
            "prompt_injection",
            "jailbreak",
            "encoding",
            "web_injection",
            "steganographic",
            "language_crossover",
        ],
    },
    "MEASURE 2.7": {
        "function": "MEASURE",
        "title": "AI System Safety and Risk Controls",
        "description": (
            "AI system safety and efficacy of risk controls are assessed."
        ),
        "categories": ["malware", "harmful_content"],
    },
    "MEASURE 2.11": {
        "function": "MEASURE",
        "title": "Fairness and Bias Evaluation",
        "description": (
            "Fairness and bias in AI system outputs are assessed. "
            "Measurements include equalized odds, demographic parity, "
            "and counterfactual fairness."
        ),
        "categories": ["bias_fairness"],
    },
    "MEASURE 3.2": {
        "function": "MEASURE",
        "title": "Risk Tracking and Management",
        "description": (
            "Risk tracking approaches are considered and applied to "
            "manage AI risks and benefits from third-party resources."
        ),
        "categories": ["rag_poisoning"],
    },
    # ──────────────────────────────────────────────────────────
    # MANAGE: Allocate resources to mapped and measured risks
    # ──────────────────────────────────────────────────────────
    "MANAGE 1.1": {
        "function": "MANAGE",
        "title": "Risk Treatment Plans",
        "description": (
            "A determination is made as to whether the AI system achieves "
            "its intended purpose and that risks are managed."
        ),
        "categories": [],
    },
    "MANAGE 2.2": {
        "function": "MANAGE",
        "title": "Mechanisms for Reliability and Robustness",
        "description": (
            "Mechanisms are in place and applied to sustain the value "
            "of deployed AI systems, including reliability and robustness "
            "monitoring."
        ),
        "categories": [
            "hallucination",
            "context_overflow",
            "denial_of_service",
        ],
    },
    "MANAGE 2.3": {
        "function": "MANAGE",
        "title": "AI System Security Controls",
        "description": (
            "Procedures are in place to manage AI system security "
            "risks, including prompt injection, jailbreak, and adversarial "
            "attacks."
        ),
        "categories": [
            "prompt_injection",
            "jailbreak",
            "encoding",
            "web_injection",
            "malware",
            "steganographic",
            "language_crossover",
            "indirect_injection",
        ],
    },
    "MANAGE 2.4": {
        "function": "MANAGE",
        "title": "Risk Monitoring and Response",
        "description": (
            "Mechanisms are in place and applied for continuous monitoring "
            "and rapid response when risks are identified."
        ),
        "categories": [],
    },
    "MANAGE 3.1": {
        "function": "MANAGE",
        "title": "Risk Communication and Documentation",
        "description": (
            "AI risks and benefits from third-party resources are assessed "
            "and communicated to relevant AI actors."
        ),
        "categories": [],
    },
    "MANAGE 3.2": {
        "function": "MANAGE",
        "title": "Data Privacy and Information Security",
        "description": (
            "Pre-trained models, third-party data, and system components "
            "are assessed for privacy, security, and information integrity."
        ),
        "categories": [
            "data_extraction",
            "pii_leakage",
        ],
    },
    "MANAGE 4.1": {
        "function": "MANAGE",
        "title": "Post-Deployment Monitoring and Incident Response",
        "description": (
            "Post-deployment AI system monitoring plans are implemented, "
            "including mechanisms for harmful content, safety incidents, "
            "and user reporting."
        ),
        "categories": [
            "toxicity",
            "harmful_content",
            "social_engineering",
            "excessive_agency",
            "function_calling",
            "role_play",
        ],
    },
    "MANAGE 4.2": {
        "function": "MANAGE",
        "title": "Decommissioning and Phase-Out",
        "description": (
            "Mechanisms are in place to manage the retirement or phase-out "
            "of AI systems safely."
        ),
        "categories": [],
    },
}

# Reverse mapping: category -> list of NIST AI RMF subcategory IDs
CATEGORY_TO_NIST: dict[str, list[str]] = {}
for _nist_id, _info in NIST_AI_RMF.items():
    for _cat in _info["categories"]:
        CATEGORY_TO_NIST.setdefault(_cat, []).append(_nist_id)
