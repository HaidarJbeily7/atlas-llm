"""Pydantic v2 data models for ATLAS scan results and findings."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field

from atlas.core.enums import (
    ComplianceStatus,
    RiskLevel,
    Severity,
    VulnerabilityCategory,
)


class Intent(BaseModel):
    """A canonical attack intent for the 2x2 factorial experiment.

    Each intent represents a single adversarial objective tested across
    all four experimental conditions (static/adaptive x single/multi-turn).
    """

    id: str
    category: str
    objective: str  # plain-language goal (used by attacker LLM)
    direct_prompt: str  # single-turn static prompt
    scripted_turns: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)


class Message(BaseModel):
    """A single message in a conversation."""

    role: str  # "system", "user", "assistant", "tool"
    content: str
    name: str | None = None
    tool_calls: list[ToolCall] | None = None
    tool_call_id: str | None = None


class ToolCall(BaseModel):
    """A tool/function call made by the LLM."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    function_name: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    type: str = "function"


class ToolResponse(BaseModel):
    """A response from a tool/function execution."""

    tool_call_id: str
    output: str
    error: str | None = None


class ToolDefinition(BaseModel):
    """Definition of a tool/function available to the LLM."""

    name: str
    description: str = ""
    parameters: dict[str, Any] = Field(default_factory=dict)


class Attempt(BaseModel):
    """A single probe attempt against an LLM."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    probe_name: str
    prompt: str
    response: str = ""
    system_prompt: str = ""
    messages: list[Message] = Field(default_factory=list)
    tool_calls: list[ToolCall] = Field(default_factory=list)
    tool_definitions: list[ToolDefinition] = Field(default_factory=list)
    images: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    # Token and cost tracking for the 2x2 experiment
    target_tokens_in: int = 0
    target_tokens_out: int = 0
    attacker_tokens_in: int = 0
    attacker_tokens_out: int = 0
    cost_usd: float = 0.0
    latency_ms: float = 0.0
    num_target_calls: int = 0
    num_attacker_calls: int = 0


class DetectorResult(BaseModel):
    """Result from a single detector evaluation."""

    detector_name: str
    passed: bool
    score: float = 0.0  # 0.0-1.0
    confidence: float = 1.0
    evidence: str = ""
    # Human review flagging (True for all LLM-judge-based detectors)
    needs_human_review: bool = False
    # Failure type classification
    failure_type: str = ""
    # LLM judge metadata (populated by llm_judge / semantic_judge detectors)
    judge_reasoning: str = ""
    judge_model: str = ""
    judge_tokens_in: int = 0
    judge_tokens_out: int = 0
    judge_cost_usd: float = 0.0
    judge_latency_ms: float = 0.0
    # Per-dimension ratings (semantic_judge)
    dimension_scores: dict[str, str] = Field(default_factory=dict)
    # Pattern-based detector details
    matched_patterns: list[str] = Field(default_factory=list)
    # The actual prompt sent to the judge (for audit/reproducibility)
    prompt_sent: str = ""


class Finding(BaseModel):
    """A security finding combining an attempt with detector results."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    attempt: Attempt
    detector_results: list[DetectorResult] = Field(default_factory=list)
    severity: Severity = Severity.MEDIUM
    category: VulnerabilityCategory = VulnerabilityCategory.OTHER
    passed: bool = True
    needs_human_review: bool = False
    description: str = ""
    remediation: str = ""
    compliance_articles: list[str] = Field(default_factory=list)
    owasp_categories: list[str] = Field(default_factory=list)


class ProbeResult(BaseModel):
    """Aggregated results from a single probe execution."""

    probe_name: str
    category: VulnerabilityCategory = VulnerabilityCategory.OTHER
    total_attempts: int = 0
    passed: int = 0
    failed: int = 0
    pass_rate: float = 0.0  # 0-100
    findings: list[Finding] = Field(default_factory=list)
    compliance_articles: list[str] = Field(default_factory=list)


class SecurityScore(BaseModel):
    """Computed security score with breakdowns."""

    overall_score: float = 0.0  # 0-100
    category_scores: dict[str, float] = Field(default_factory=dict)
    risk_level: RiskLevel = RiskLevel.HIGH
    vulnerabilities_by_severity: dict[str, int] = Field(
        default_factory=lambda: {
            "critical": 0,
            "high": 0,
            "medium": 0,
            "low": 0,
            "info": 0,
        }
    )
    compliance_score: float = 0.0
    weighted_failure_rate: float = 0.0


class ArticleAssessment(BaseModel):
    """Assessment of a single EU AI Act article."""

    article_id: str
    title: str = ""
    status: ComplianceStatus = ComplianceStatus.NOT_ASSESSED
    findings_count: int = 0
    critical_findings: int = 0
    risk_score: float = 0.0
    relevant_probes: list[str] = Field(default_factory=list)


class ComplianceAssessment(BaseModel):
    """Overall EU AI Act compliance assessment."""

    overall_status: ComplianceStatus = ComplianceStatus.NOT_ASSESSED
    articles_assessed: int = 0
    articles_passed: int = 0
    articles_failed: int = 0
    high_risk_areas: list[str] = Field(default_factory=list)
    required_actions: list[str] = Field(default_factory=list)
    article_details: list[ArticleAssessment] = Field(default_factory=list)


class ScanResult(BaseModel):
    """Complete result of a security scan."""

    scan_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    model_name: str = ""
    provider: str = ""
    profile: str = ""
    started_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime | None = None
    duration_ms: float = 0.0
    probe_results: dict[str, ProbeResult] = Field(default_factory=dict)
    findings: list[Finding] = Field(default_factory=list)
    security_score: SecurityScore = Field(default_factory=SecurityScore)
    compliance_assessment: ComplianceAssessment = Field(
        default_factory=ComplianceAssessment
    )
    recommendations: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    # Aggregate cost/token metrics
    total_cost_usd: float = 0.0
    total_target_tokens: int = 0
    total_attacker_tokens: int = 0


class ModelScore(BaseModel):
    """Score breakdown for a single model in a comparison."""

    model_name: str
    overall_score: float = 0.0
    category_scores: dict[str, float] = Field(default_factory=dict)
    risk_level: RiskLevel = RiskLevel.HIGH
    pass_rate: float = 0.0
    total_findings: int = 0
    failed_findings: int = 0


class ComparisonResult(BaseModel):
    """Result of comparing multiple models on the same probes."""

    comparison_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    models: list[str] = Field(default_factory=list)
    scan_results: dict[str, ScanResult] = Field(default_factory=dict)
    leaderboard: list[ModelScore] = Field(default_factory=list)
    started_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime | None = None
    duration_ms: float = 0.0
    metadata: dict[str, Any] = Field(default_factory=dict)
