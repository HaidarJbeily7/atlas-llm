"""Core models, enums, protocols, and error types for ATLAS."""

from atlas.core.enums import (
    ComplianceStatus,
    OutputFormat,
    RiskLevel,
    Severity,
    VulnerabilityCategory,
)
from atlas.core.errors import (
    AtlasConfigError,
    AtlasConnectionError,
    AtlasError,
    AtlasExecutionError,
    AtlasTimeoutError,
    AtlasValidationError,
    DatasetError,
    PluginError,
    ResultProcessingError,
    is_transient_error,
    retry_on_transient_error,
)
from atlas.core.models import (
    ArticleAssessment,
    Attempt,
    ComplianceAssessment,
    DetectorResult,
    Finding,
    ProbeResult,
    ScanResult,
    SecurityScore,
)
from atlas.core.protocols import (
    Detector,
    Evaluator,
    Generator,
    Probe,
    Reporter,
)

__all__ = [
    # Enums
    "ComplianceStatus",
    "OutputFormat",
    "RiskLevel",
    "Severity",
    "VulnerabilityCategory",
    # Errors
    "AtlasConfigError",
    "AtlasConnectionError",
    "AtlasError",
    "AtlasExecutionError",
    "AtlasTimeoutError",
    "AtlasValidationError",
    "DatasetError",
    "PluginError",
    "ResultProcessingError",
    "is_transient_error",
    "retry_on_transient_error",
    # Models
    "ArticleAssessment",
    "Attempt",
    "ComplianceAssessment",
    "DetectorResult",
    "Finding",
    "ProbeResult",
    "ScanResult",
    "SecurityScore",
    # Protocols
    "Detector",
    "Evaluator",
    "Generator",
    "Probe",
    "Reporter",
]
