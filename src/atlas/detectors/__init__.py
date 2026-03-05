"""Detectors for classifying LLM responses."""
from atlas.detectors.base import (
    BaseDetector,
    AnyOfDetector,
    AllOfDetector,
    NoneOfDetector,
    any_of,
    all_of,
    none_of,
)
from atlas.detectors.keyword import KeywordDetector
from atlas.detectors.refusal import RefusalDetector

__all__ = [
    "BaseDetector",
    "AnyOfDetector",
    "AllOfDetector",
    "NoneOfDetector",
    "any_of",
    "all_of",
    "none_of",
    "KeywordDetector",
    "RefusalDetector",
]

# Detector name -> class mapping for registry fallback
DETECTOR_REGISTRY = {
    "keyword": "atlas.detectors.keyword.KeywordDetector",
    "refusal": "atlas.detectors.refusal.RefusalDetector",
    "similarity": "atlas.detectors.similarity.SimilarityDetector",
    "llm_judge": "atlas.detectors.llm_judge.LLMJudgeDetector",
}
