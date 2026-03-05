"""Security probes for LLM vulnerability testing."""
from atlas.probes.base import BaseProbe

__all__ = ["BaseProbe"]

# Probe name -> module path mapping for lazy loading
PROBE_MODULES = {
    "prompt_injection": "atlas.probes.prompt_injection",
    "jailbreak": "atlas.probes.jailbreak",
    "encoding": "atlas.probes.encoding",
    "extraction": "atlas.probes.extraction",
    "toxicity": "atlas.probes.toxicity",
    "hallucination": "atlas.probes.hallucination",
    "web_injection": "atlas.probes.web_injection",
    "malware": "atlas.probes.malware",
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
}
