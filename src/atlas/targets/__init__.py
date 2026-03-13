"""Target adapters for ATLAS scan targets."""
from atlas.targets.base import BaseTarget
from atlas.targets.http_target import HTTPTarget
from atlas.targets.llm_target import LLMTarget
from atlas.targets.rag_target import RAGTarget

__all__ = [
    "BaseTarget",
    "HTTPTarget",
    "LLMTarget",
    "RAGTarget",
]
