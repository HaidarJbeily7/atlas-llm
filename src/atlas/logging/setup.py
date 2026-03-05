"""Structured logging setup for ATLAS using structlog."""
from __future__ import annotations

import logging
import sys
import uuid
from contextlib import contextmanager
from time import time
from typing import Any, Generator

import structlog

_SESSION_ID: str | None = None
_INITIALIZED = False


def get_session_id() -> str:
    """Get or create a session ID for log correlation."""
    global _SESSION_ID
    if _SESSION_ID is None:
        _SESSION_ID = uuid.uuid4().hex[:8]
    return _SESSION_ID


def setup_logging(
    level: str = "INFO",
    format_type: str = "console",
    output: str = "stdout",
) -> None:
    """Configure structlog for ATLAS.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        format_type: "json" for structured JSON, "console" for human-readable
        output: "stdout", "stderr", or a file path
    """
    global _INITIALIZED

    log_level = getattr(logging, level.upper(), logging.INFO)

    # Configure standard library logging
    logging.basicConfig(format="%(message)s", level=log_level, force=True)

    # Suppress noisy loggers
    for name in ("httpx", "httpcore", "urllib3", "litellm", "openai"):
        logging.getLogger(name).setLevel(logging.WARNING)

    shared_processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
    ]

    if format_type == "json":
        renderer = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer(colors=output == "stdout")

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Set up the formatter for stdlib handler
    formatter = structlog.stdlib.ProcessorFormatter(
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
    )

    root = logging.getLogger()
    root.handlers.clear()

    if output in ("stdout", "stderr"):
        handler = logging.StreamHandler(sys.stdout if output == "stdout" else sys.stderr)
    else:
        handler = logging.FileHandler(output)

    handler.setFormatter(formatter)
    root.addHandler(handler)
    root.setLevel(log_level)

    _INITIALIZED = True


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Get a configured logger with session context."""
    global _INITIALIZED
    if not _INITIALIZED:
        setup_logging()
    return structlog.get_logger(name).bind(session_id=get_session_id())


def _mask_secrets(config: dict[str, Any]) -> dict[str, Any]:
    """Mask sensitive values in config dicts."""
    sensitive = {"api_key", "secret", "password", "token", "credentials"}
    masked = {}
    for k, v in config.items():
        if isinstance(v, dict):
            masked[k] = _mask_secrets(v)
        elif any(s in k.lower() for s in sensitive) and isinstance(v, str) and len(v) > 4:
            masked[k] = v[:4] + "****"
        else:
            masked[k] = v
    return masked


@contextmanager
def log_execution_context(
    command: str, config: dict[str, Any] | None = None
) -> Generator[None, None, None]:
    """Context manager for automatic timing and error logging."""
    log = get_logger("atlas.execution")
    start = time()
    safe_config = _mask_secrets(config) if config else {}
    log.info("execution_start", command=command, config=safe_config)

    try:
        yield
    except Exception as e:
        elapsed = (time() - start) * 1000
        log.error("execution_error", command=command, error=str(e), duration_ms=elapsed, exc_info=True)
        raise
    else:
        elapsed = (time() - start) * 1000
        log.info("execution_end", command=command, duration_ms=elapsed, status="success")
