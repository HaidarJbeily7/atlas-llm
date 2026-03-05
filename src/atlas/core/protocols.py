"""Runtime-checkable Protocol classes defining ATLAS plugin interfaces."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from atlas.core.enums import VulnerabilityCategory
from atlas.core.models import Attempt, DetectorResult, Finding, ProbeResult, ScanResult


@runtime_checkable
class Probe(Protocol):
    """Protocol for security probes that generate test prompts."""

    name: str
    category: VulnerabilityCategory
    tags: list[str]

    def generate_prompts(self) -> list[Attempt]: ...


@runtime_checkable
class Generator(Protocol):
    """Protocol for LLM generators that produce responses."""

    model_name: str

    async def generate(self, prompt: str, **kwargs: Any) -> str: ...

    async def generate_batch(
        self, prompts: list[str], **kwargs: Any
    ) -> list[str]: ...


@runtime_checkable
class Detector(Protocol):
    """Protocol for detectors that evaluate LLM responses."""

    name: str

    async def detect(self, attempt: Attempt) -> DetectorResult: ...


@runtime_checkable
class Evaluator(Protocol):
    """Protocol for evaluators that aggregate findings into assessments."""

    name: str

    def evaluate(self, findings: list[Finding]) -> dict[str, Any]: ...


@runtime_checkable
class Reporter(Protocol):
    """Protocol for reporters that generate output from scan results."""

    name: str
    format: str

    async def generate(self, result: ScanResult, output_path: str) -> str: ...
