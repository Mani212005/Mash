"""
Mash Voice - Structured Logging Utilities
"""

import logging
import sys
from typing import Any

import structlog
from structlog.types import Processor

from app.config import get_settings


def setup_logging() -> None:
    """Configure structured logging for the application."""
    settings = get_settings()

    # Shared processors for all loggers
    shared_processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.stdlib.ExtraAdder(),
    ]

    # Configure structlog
    structlog.configure(
        processors=shared_processors
        + [
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Configure standard library logging
    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared_processors,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            structlog.dev.ConsoleRenderer(colors=True)
            if settings.debug
            else structlog.processors.JSONRenderer(),
        ],
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.addHandler(handler)
    root_logger.setLevel(settings.log_level)

    # Reduce noise from third-party libraries
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("websockets").setLevel(logging.WARNING)


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Get a structured logger instance."""
    return structlog.stdlib.get_logger(name)


class CallLogger:
    """Logger with call context automatically injected."""

    def __init__(self, call_sid: str):
        self.logger = get_logger("call")
        self.call_sid = call_sid

    def _log(self, level: str, event: str, **kwargs: Any) -> None:
        log_method = getattr(self.logger, level)
        log_method(event, call_sid=self.call_sid, **kwargs)

    def info(self, event: str, **kwargs: Any) -> None:
        self._log("info", event, **kwargs)

    def debug(self, event: str, **kwargs: Any) -> None:
        self._log("debug", event, **kwargs)

    def warning(self, event: str, **kwargs: Any) -> None:
        self._log("warning", event, **kwargs)

    def error(self, event: str, **kwargs: Any) -> None:
        self._log("error", event, **kwargs)

    def exception(self, event: str, **kwargs: Any) -> None:
        self._log("exception", event, **kwargs)
