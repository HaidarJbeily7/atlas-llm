"""Security probes for LLM vulnerability testing."""
from atlas.probes.base import AdaptiveProbe, BaseProbe, ConversationalProbe

__all__ = ["AdaptiveProbe", "BaseProbe", "ConversationalProbe"]

# Probe name -> module path mapping for lazy loading
PROBE_MODULES = {
    # Original probes
    "prompt_injection": "atlas.probes.prompt_injection",
    "jailbreak": "atlas.probes.jailbreak",
    "encoding": "atlas.probes.encoding",
    "extraction": "atlas.probes.extraction",
    "toxicity": "atlas.probes.toxicity",
    "hallucination": "atlas.probes.hallucination",
    "web_injection": "atlas.probes.web_injection",
    "malware": "atlas.probes.malware",
    "agent_harm": "atlas.probes.agent_harm",
    # Multi-turn probes
    "crescendo": "atlas.probes.crescendo",
    "multi_turn_injection": "atlas.probes.multi_turn_injection",
    # Tier 1 probes
    "pii_leakage": "atlas.probes.pii_leakage",
    "bias_fairness": "atlas.probes.bias_fairness",
    "excessive_agency": "atlas.probes.excessive_agency",
    "denial_of_service": "atlas.probes.denial_of_service",
    "rag_poisoning": "atlas.probes.rag_poisoning",
    "function_calling": "atlas.probes.function_calling_probe",
    # Tier 2 probes
    "indirect_injection": "atlas.probes.indirect_injection",
    "language_crossover": "atlas.probes.language_crossover",
    "role_play": "atlas.probes.role_play",
    "context_overflow": "atlas.probes.context_overflow",
    "steganographic": "atlas.probes.steganographic",
    "social_engineering": "atlas.probes.social_engineering",
    # Multimodal probes
    "visual_injection": "atlas.probes.visual_injection",
    # Experiment probes (2x2 factorial)
    "direct_single_turn": "atlas.probes.direct_single_turn",
    "scripted_multi_turn": "atlas.probes.scripted_multi_turn",
    "adaptive_single_query_st": "atlas.probes.adaptive_single_query_single_turn",
    "adaptive_single_turn": "atlas.probes.adaptive_single_turn",
    "adaptive_multi_turn": "atlas.probes.adaptive_multi_turn",
    "best_of_k_st": "atlas.probes.best_of_k_single_turn",
}

# Mapping from probe category to recommended default detectors
DEFAULT_PROBE_DETECTORS = {
    "prompt_injection": ["keyword", "refusal"],
    "jailbreak": ["keyword", "refusal"],
    "encoding": ["keyword"],
    "extraction": ["keyword"],
    "toxicity": ["refusal", "keyword"],
    "hallucination": ["llm_judge"],
    "web_injection": ["keyword"],
    "malware": ["refusal"],
    "agent_harm": ["refusal", "keyword"],
    "crescendo": ["keyword", "refusal"],
    "multi_turn_injection": ["keyword", "refusal"],
    "pii_leakage": ["keyword"],
    "bias_fairness": ["keyword"],
    "excessive_agency": ["keyword"],
    "denial_of_service": ["keyword"],
    "rag_poisoning": ["keyword"],
    "function_calling": ["keyword", "tool_call"],
    "indirect_injection": ["keyword"],
    "language_crossover": ["keyword"],
    "role_play": ["refusal"],
    "context_overflow": ["keyword"],
    "steganographic": ["keyword"],
    "social_engineering": ["refusal"],
    "visual_injection": ["keyword", "refusal"],
    "scripted_multi_turn": ["keyword", "refusal"],
    "adaptive_single_query_st": ["keyword", "refusal"],
    "adaptive_single_turn": ["keyword", "refusal"],
    "adaptive_multi_turn": ["keyword", "refusal"],
    "best_of_k_st": ["keyword", "refusal"],
}
