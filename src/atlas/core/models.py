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


class Attempt(BaseModel):
    """A single probe attempt against an LLM."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    probe_name: str
    prompt: str
    response: str = ""
    system_prompt: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class DetectorResult(BaseModel):
    """Result from a single detector evaluation."""

    detector_name: str
    passed: bool
    score: float = 0.0  # 0.0-1.0
    confidence: float = 1.0
    evidence: str = ""


class Finding(BaseModel):
    """A security finding combining an attempt with detector results."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    attempt: Attempt
    detector_results: list[DetectorResult] = Field(default_factory=list)
    severity: Severity = Severity.MEDIUM
    category: VulnerabilityCategory = VulnerabilityCategory.OTHER
    passed: bool = True
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
