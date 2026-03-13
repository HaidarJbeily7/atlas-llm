"""Built-in scan profiles for ATLAS."""
from __future__ import annotations

from atlas.config.models import ProfileConfig, ScanConfig

QUICK_PROFILE = ProfileConfig(
    name="quick",
    description="Quick smoke test with essential probes",
    probes=["jailbreak", "prompt_injection"],
    detectors=["keyword", "refusal"],
    scan=ScanConfig(concurrency=5, timeout=120, probe_timeout=60),
)

STANDARD_PROFILE = ProfileConfig(
    name="standard",
    description="Standard security assessment covering core vulnerability categories",
    probes=[
        "prompt_injection",
        "jailbreak",
        "extraction",
        "toxicity",
        "hallucination",
        "pii_leakage",
        "excessive_agency",
    ],
    detectors=["keyword", "refusal", "llm_judge"],
    compliance_tags=["article-9", "article-15"],
    scan=ScanConfig(concurrency=10, timeout=300, probe_timeout=120),
)

FULL_PROFILE = ProfileConfig(
    name="full",
    description="Comprehensive assessment with all probes and compliance mapping",
    probes=[
        "prompt_injection",
        "jailbreak",
        "encoding",
        "extraction",
        "toxicity",
        "hallucination",
        "web_injection",
        "malware",
        "pii_leakage",
        "bias_fairness",
        "excessive_agency",
        "denial_of_service",
        "rag_poisoning",
        "function_calling",
        "indirect_injection",
        "language_crossover",
        "role_play",
        "context_overflow",
        "steganographic",
        "social_engineering",
    ],
    detectors=["keyword", "refusal", "llm_judge"],
    compliance_tags=[
        "article-9", "article-10", "article-13", "article-14",
        "article-15", "article-50", "article-53", "article-55",
        "annex-iv",
    ],
    scan=ScanConfig(concurrency=10, timeout=3600, probe_timeout=180),
)

MULTI_TURN_PROFILE = ProfileConfig(
    name="multi-turn",
    description="Multi-turn and adaptive attack probes",
    probes=[
        "crescendo",
        "multi_turn_injection",
    ],
    detectors=["keyword", "refusal"],
    scan=ScanConfig(concurrency=5, timeout=600, probe_timeout=300),
)

CI_PROFILE = ProfileConfig(
    name="ci",
    description="Fast CI/CD-optimized profile for pipeline integration",
    probes=[
        "prompt_injection",
        "jailbreak",
        "pii_leakage",
        "toxicity",
    ],
    detectors=["keyword", "refusal"],
    scan=ScanConfig(concurrency=5, timeout=180, probe_timeout=60),
)

BUILTIN_PROFILES: dict[str, ProfileConfig] = {
    "quick": QUICK_PROFILE,
    "standard": STANDARD_PROFILE,
    "full": FULL_PROFILE,
    "multi-turn": MULTI_TURN_PROFILE,
    "ci": CI_PROFILE,
}


def get_profile(name: str) -> ProfileConfig:
    """Get a built-in profile by name."""
    if name not in BUILTIN_PROFILES:
        available = list(BUILTIN_PROFILES.keys())
        raise ValueError(f"Unknown profile: {name}. Available: {available}")
    return BUILTIN_PROFILES[name]
