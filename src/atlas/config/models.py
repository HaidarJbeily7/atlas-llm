"""Configuration models for ATLAS."""
from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator

from atlas.core.enums import OutputFormat


class ProviderConfig(BaseModel):
    """LLM provider configuration."""
    model: str = "openai/gpt-4o"  # LiteLLM model string
    api_key: str | None = None
    api_base: str | None = None
    timeout: int = Field(default=30, ge=1, le=600)
    max_retries: int = Field(default=3, ge=0, le=10)
    temperature: float = Field(default=0.0, ge=0.0, le=2.0)
    max_tokens: int | None = None
    extra: dict[str, Any] = Field(default_factory=dict)


class ProbeConfig(BaseModel):
    """Configuration for a probe."""
    name: str
    enabled: bool = True
    detector: str = "keyword"
    detector_config: dict[str, Any] = Field(default_factory=dict)
    max_samples: int | None = None


class ScanConfig(BaseModel):
    """Scan execution configuration."""
    concurrency: int = Field(default=10, ge=1, le=100)
    timeout: int = Field(default=600, ge=1, le=72000)
    probe_timeout: int = Field(default=120, ge=1, le=6000)
    continue_on_error: bool = False
    checkpoint_enabled: bool = True
    checkpoint_dir: str = ".atlas/checkpoints"


class OutputConfig(BaseModel):
    """Output configuration."""
    directory: str = "./results"
    format: OutputFormat = OutputFormat.JSON
    include_timestamps: bool = True
    include_evidence: bool = True


class LoggingConfig(BaseModel):
    """Logging configuration."""
    level: str = "INFO"
    format: str = "console"  # "json" or "console"
    output: str = "stdout"


class ComplianceConfig(BaseModel):
    """Compliance framework configuration."""
    eu_ai_act: bool = True
    owasp_llm: bool = True
    risk_threshold: float = Field(default=0.7, ge=0.0, le=1.0)
    strict_mode: bool = False


class ProfileConfig(BaseModel):
    """A named test profile."""
    name: str
    description: str = ""
    probes: list[str] = Field(default_factory=list)
    detectors: list[str] = Field(default_factory=list)
    compliance_tags: list[str] = Field(default_factory=list)
    scan: ScanConfig = Field(default_factory=ScanConfig)


class AtlasConfig(BaseModel):
    """Root ATLAS configuration."""
    provider: ProviderConfig = Field(default_factory=ProviderConfig)
    scan: ScanConfig = Field(default_factory=ScanConfig)
    output: OutputConfig = Field(default_factory=OutputConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    compliance: ComplianceConfig = Field(default_factory=ComplianceConfig)
    profiles: dict[str, ProfileConfig] = Field(default_factory=dict)
    probes: list[ProbeConfig] = Field(default_factory=list)
