"""Enumerations for ATLAS core types."""

from enum import Enum


class Severity(str, Enum):
    """Severity levels for security findings."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class RiskLevel(str, Enum):
    """Overall risk assessment levels."""

    MINIMAL = "minimal"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class VulnerabilityCategory(str, Enum):
    """Categories of LLM security vulnerabilities."""

    PROMPT_INJECTION = "prompt_injection"
    JAILBREAK = "jailbreak"
    DATA_EXTRACTION = "data_extraction"
    TOXICITY = "toxicity"
    HALLUCINATION = "hallucination"
    MALWARE = "malware"
    WEB_INJECTION = "web_injection"
    ENCODING = "encoding"
    HARMFUL_CONTENT = "harmful_content"
    OTHER = "other"


class ComplianceStatus(str, Enum):
    """EU AI Act compliance assessment status."""

    COMPLIANT = "compliant"
    NON_COMPLIANT = "non-compliant"
    PARTIAL = "partial"
    NOT_ASSESSED = "not-assessed"


class OutputFormat(str, Enum):
    """Supported report output formats."""

    JSON = "json"
    HTML = "html"
    MARKDOWN = "markdown"
    PDF = "pdf"
