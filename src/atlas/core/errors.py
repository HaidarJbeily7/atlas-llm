"""
Custom exception hierarchy for ATLAS.

Provides structured exceptions with actionable troubleshooting guidance,
retry logic with exponential backoff, and transient error detection.

Ported from SCI's garak exception hierarchy with Atlas-specific naming.
"""

import functools
import logging
import random
import time
from typing import Any, Callable, Optional, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


# =============================================================================
# Exception Hierarchy
# =============================================================================


class AtlasError(Exception):
    """
    Base exception for all ATLAS-related errors.

    Provides structured error information with troubleshooting guidance.

    Attributes:
        message: Human-readable error message.
        error_code: Unique error code for categorization.
        context: Additional context dictionary.
        troubleshooting_tips: List of actionable suggestions.
    """

    def __init__(
        self,
        message: str,
        error_code: str = "ATLAS_000",
        troubleshooting_tips: Optional[list[str]] = None,
        context: Optional[dict[str, Any]] = None,
    ) -> None:
        self.message = message
        self.error_code = error_code
        self.troubleshooting_tips = troubleshooting_tips or []
        self.context = context or {}
        super().__init__(self._format_message())

    def _format_message(self) -> str:
        """Format error message with troubleshooting guidance."""
        parts = [f"[{self.error_code}] {self.message}"]

        if self.troubleshooting_tips:
            parts.append("\n\nTroubleshooting:")
            for i, tip in enumerate(self.troubleshooting_tips, 1):
                parts.append(f"  {i}. {tip}")

        if self.context:
            context_items = ", ".join(f"{k}={v}" for k, v in self.context.items())
            parts.append(f"\n\nContext: {context_items}")

        return "\n".join(parts) if len(parts) > 1 else parts[0]

    def __str__(self) -> str:
        return self._format_message()

    @classmethod
    def from_exception(
        cls,
        exc: Exception,
        context: Optional[dict[str, Any]] = None,
        error_code: Optional[str] = None,
    ) -> "AtlasError":
        """Create an AtlasError from a standard exception."""
        ctx = context or {}
        ctx["original_exception"] = type(exc).__name__

        return cls(
            message=str(exc),
            error_code=error_code or "ATLAS_001",
            troubleshooting_tips=["Check the original error message for details"],
            context=ctx,
        )


class AtlasConfigError(AtlasError):
    """
    Configuration validation failures.

    Raised when configuration is invalid, missing required fields,
    or contains unsupported values.

    Attributes:
        field_name: Name of the invalid configuration field.
    """

    def __init__(
        self,
        message: str,
        field_name: Optional[str] = None,
        error_code: str = "CONFIG_001",
        troubleshooting_tips: Optional[list[str]] = None,
        context: Optional[dict[str, Any]] = None,
    ) -> None:
        self.field_name = field_name

        ctx = context or {}
        if field_name:
            ctx["field_name"] = field_name

        tips = troubleshooting_tips or [
            "Check your configuration file for syntax errors",
            "Verify all required fields are present",
            "See documentation for configuration examples",
        ]

        super().__init__(
            message=message,
            error_code=error_code,
            troubleshooting_tips=tips,
            context=ctx,
        )


class AtlasConnectionError(AtlasError):
    """
    Network/connectivity issues.

    Raised when there are API connection failures, authentication
    errors, or network timeouts.

    Attributes:
        provider: Name of the provider that failed.
        retry_count: Number of retry attempts made.
    """

    def __init__(
        self,
        message: str,
        provider: Optional[str] = None,
        retry_count: int = 0,
        error_code: str = "CONN_001",
        troubleshooting_tips: Optional[list[str]] = None,
        context: Optional[dict[str, Any]] = None,
    ) -> None:
        self.provider = provider
        self.retry_count = retry_count

        ctx = context or {}
        if provider:
            ctx["provider"] = provider
        ctx["retry_count"] = retry_count

        tips = troubleshooting_tips or [
            "Check your internet connectivity",
            "Verify the API endpoint is accessible",
            "Verify your API credentials are correct",
            "Check the provider's status page for outages",
        ]

        super().__init__(
            message=message,
            error_code=error_code,
            troubleshooting_tips=tips,
            context=ctx,
        )


class AtlasExecutionError(AtlasError):
    """
    Scan execution failures.

    Raised when probe execution fails, detector errors occur,
    or the scan engine encounters a runtime error.

    Attributes:
        probe_name: Name of the probe that failed.
    """

    def __init__(
        self,
        message: str,
        probe_name: Optional[str] = None,
        error_code: str = "EXEC_001",
        troubleshooting_tips: Optional[list[str]] = None,
        context: Optional[dict[str, Any]] = None,
    ) -> None:
        self.probe_name = probe_name

        ctx = context or {}
        if probe_name:
            ctx["probe_name"] = probe_name

        tips = troubleshooting_tips or [
            "Check the error message for specific details",
            "Ensure all probe names are valid",
            "Verify the target model is accessible",
        ]

        super().__init__(
            message=message,
            error_code=error_code,
            troubleshooting_tips=tips,
            context=ctx,
        )


class AtlasTimeoutError(AtlasError):
    """
    Timeout-related errors.

    Raised when operations exceed their time limits.

    Attributes:
        operation: Name of the operation that timed out.
        timeout_seconds: Configured timeout limit.
        elapsed_seconds: Time elapsed before timeout.
    """

    def __init__(
        self,
        message: str,
        operation: Optional[str] = None,
        timeout_seconds: Optional[float] = None,
        elapsed_seconds: Optional[float] = None,
        error_code: str = "TIMEOUT_001",
        troubleshooting_tips: Optional[list[str]] = None,
        context: Optional[dict[str, Any]] = None,
    ) -> None:
        self.operation = operation
        self.timeout_seconds = timeout_seconds
        self.elapsed_seconds = elapsed_seconds

        ctx = context or {}
        if operation:
            ctx["operation"] = operation
        if timeout_seconds is not None:
            ctx["timeout_seconds"] = timeout_seconds
        if elapsed_seconds is not None:
            ctx["elapsed_seconds"] = round(elapsed_seconds, 2)

        tips = troubleshooting_tips or [
            f"Increase the timeout value (current: {timeout_seconds}s)"
            if timeout_seconds
            else "Increase the timeout value",
            "Reduce the number of probes in the scan",
            "Check network connectivity to the LLM provider",
            "Consider running with fewer parallel executions",
        ]

        super().__init__(
            message=message,
            error_code=error_code,
            troubleshooting_tips=tips,
            context=ctx,
        )


class AtlasValidationError(AtlasError):
    """
    Pre-execution validation failures.

    Raised when probes, detectors, or configurations are not available
    or incompatible.

    Attributes:
        validation_type: Type of validation that failed.
        suggestions: List of suggested alternatives.
    """

    def __init__(
        self,
        message: str,
        validation_type: Optional[str] = None,
        suggestions: Optional[list[str]] = None,
        error_code: str = "VAL_001",
        troubleshooting_tips: Optional[list[str]] = None,
        context: Optional[dict[str, Any]] = None,
    ) -> None:
        self.validation_type = validation_type
        self.suggestions = suggestions or []

        ctx = context or {}
        if validation_type:
            ctx["validation_type"] = validation_type
        if suggestions:
            ctx["suggestions"] = suggestions[:5]

        tips = troubleshooting_tips or []
        if not tips and suggestions:
            tips = [f"Did you mean: {', '.join(suggestions[:3])}?"]
        if not tips:
            tips = [
                "Check the spelling of probe/detector names",
                "Run 'atlas list probes' to see available probes",
                "Run 'atlas list detectors' to see available detectors",
            ]

        super().__init__(
            message=message,
            error_code=error_code,
            troubleshooting_tips=tips,
            context=ctx,
        )


class ResultProcessingError(AtlasError):
    """
    Result processing failures.

    Raised when scan results cannot be parsed, aggregated,
    or transformed into the expected output format.
    """

    def __init__(
        self,
        message: str,
        error_code: str = "RESULT_001",
        troubleshooting_tips: Optional[list[str]] = None,
        context: Optional[dict[str, Any]] = None,
    ) -> None:
        tips = troubleshooting_tips or [
            "Check that scan output files are not corrupted",
            "Verify the output format is supported",
            "Try re-running the scan",
        ]

        super().__init__(
            message=message,
            error_code=error_code,
            troubleshooting_tips=tips,
            context=context,
        )


class DatasetError(AtlasError):
    """
    Dataset loading issues.

    Raised when datasets cannot be found, loaded, or parsed.
    """

    def __init__(
        self,
        message: str,
        error_code: str = "DATASET_001",
        troubleshooting_tips: Optional[list[str]] = None,
        context: Optional[dict[str, Any]] = None,
    ) -> None:
        tips = troubleshooting_tips or [
            "Check that the dataset path exists and is accessible",
            "Verify the dataset format is supported",
            "Ensure the dataset is not corrupted or empty",
        ]

        super().__init__(
            message=message,
            error_code=error_code,
            troubleshooting_tips=tips,
            context=context,
        )


class PluginError(AtlasError):
    """
    Plugin discovery/loading issues.

    Raised when plugins cannot be found, loaded, or initialized.
    """

    def __init__(
        self,
        message: str,
        error_code: str = "PLUGIN_001",
        troubleshooting_tips: Optional[list[str]] = None,
        context: Optional[dict[str, Any]] = None,
    ) -> None:
        tips = troubleshooting_tips or [
            "Check that the plugin is installed correctly",
            "Verify the plugin entry point is registered",
            "Ensure plugin dependencies are satisfied",
        ]

        super().__init__(
            message=message,
            error_code=error_code,
            troubleshooting_tips=tips,
            context=context,
        )


# =============================================================================
# Transient Error Detection
# =============================================================================


def is_transient_error(exc: Exception) -> bool:
    """
    Determine if an exception represents a transient error that can be retried.

    Args:
        exc: The exception to check.

    Returns:
        True if the error is transient and can be retried.
    """
    # Atlas-specific transient types
    if isinstance(exc, AtlasConnectionError):
        return True
    if isinstance(exc, AtlasTimeoutError):
        return True

    # Standard transient exception types
    transient_exception_types = (
        ConnectionError,
        TimeoutError,
        ConnectionResetError,
        BrokenPipeError,
    )
    if isinstance(exc, transient_exception_types):
        return True

    # Check for HTTP status codes and patterns in the message
    error_message = str(exc).lower()

    # Rate limiting (429)
    if "429" in error_message or "rate limit" in error_message:
        return True

    # Server errors (5xx)
    server_error_patterns = [
        "502",
        "503",
        "504",
        "bad gateway",
        "service unavailable",
        "gateway timeout",
    ]
    if any(pattern in error_message for pattern in server_error_patterns):
        return True

    # Connection/network errors
    connection_patterns = [
        "timeout",
        "connection reset",
        "temporarily unavailable",
        "connection refused",
        "network unreachable",
        "connection timed out",
        "read timed out",
    ]
    if any(pattern in error_message for pattern in connection_patterns):
        return True

    return False


# =============================================================================
# Retry Decorator with Exponential Backoff
# =============================================================================


def retry_on_transient_error(
    max_attempts: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 30.0,
    backoff_factor: float = 2.0,
    retriable_exceptions: Optional[tuple[type[Exception], ...]] = None,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Decorator that retries a function on transient errors with exponential backoff and jitter.

    Args:
        max_attempts: Maximum number of retry attempts.
        initial_delay: Initial delay between retries in seconds.
        max_delay: Maximum delay between retries in seconds.
        backoff_factor: Multiplier for exponential backoff.
        retriable_exceptions: Tuple of exception types to retry on.
            If None, uses is_transient_error() to determine retryability.

    Returns:
        Decorated function that retries on transient errors.

    Example:
        >>> @retry_on_transient_error(max_attempts=3, initial_delay=1.0)
        ... def call_api():
        ...     # API call that might fail transiently
        ...     pass
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            last_exception: Optional[Exception] = None

            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as exc:
                    last_exception = exc

                    # Check if exception is retriable
                    should_retry = False
                    if retriable_exceptions:
                        should_retry = isinstance(exc, retriable_exceptions)
                    else:
                        should_retry = is_transient_error(exc)

                    if not should_retry or attempt >= max_attempts - 1:
                        raise

                    # Calculate delay with exponential backoff and jitter
                    delay = min(
                        initial_delay * (backoff_factor**attempt), max_delay
                    )
                    jitter = random.uniform(0, delay * 0.1)  # noqa: S311
                    total_delay = delay + jitter

                    logger.warning(
                        "Retry attempt %d/%d for %s after %.2fs "
                        "(error: %s: %s)",
                        attempt + 1,
                        max_attempts,
                        func.__name__,
                        total_delay,
                        type(exc).__name__,
                        str(exc)[:200],
                    )

                    time.sleep(total_delay)

            # Should never reach here, but just in case
            if last_exception:
                raise last_exception
            raise RuntimeError("Unexpected retry loop exit")

        return wrapper

    return decorator


__all__ = [
    # Base exception
    "AtlasError",
    # Specific exceptions
    "AtlasConfigError",
    "AtlasConnectionError",
    "AtlasExecutionError",
    "AtlasTimeoutError",
    "AtlasValidationError",
    "ResultProcessingError",
    "DatasetError",
    "PluginError",
    # Retry logic
    "is_transient_error",
    "retry_on_transient_error",
]
