"""twosteps_logger package root."""
import logging
import sys
from typing import Dict, List, Any, Optional

from .formatters import JsonFormatter
from .constants import StatusType
from .get_logger import (
    twosteps_logger,
    get_logger,
    setup_logger,
    get_additional,
    set_request_context,
    clear_request_context,
)

__version__ = "1.0.2"
__all__ = [
    "CustomLogger",
    "twosteps_logger",
    "get_logger",
    "setup_logger",
    "get_additional",
    "set_request_context",
    "clear_request_context",
    "StatusType",
]

# LogRecord reserved - cannot use in extra
_RESERVED = {
    "name", "msg", "args", "message", "pathname", "filename", "module", "lineno",
    "funcName", "created", "msecs", "levelname", "levelno", "process", "processName",
    "thread", "threadName", "exc_info", "exc_text", "stack_info", "relativeCreated",
    "taskName", "asctime",
}


class _ConsoleFormatter(logging.Formatter):
    """Console formatter - no traceback (traceback goes to ES only)."""

    def formatException(self, exc_info):
        return ""


def _filter_extra(extra: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Remove reserved keys, map 'name' -> 'user_name' for auth."""
    if not extra:
        return {}
    out = {}
    for k, v in extra.items():
        if k in _RESERVED:
            if k == "name" and v is not None:
                out["user_name"] = v
            continue
        out[k] = v
    return out


class CustomLogger(logging.Logger):
    """
    Custom logger (inherits logging.Logger).
    Logs go to console + OpenTelemetry Collector.
    """

    def __init__(
        self,
        name: str,
        level: int = logging.INFO,
        elastic_hosts: Optional[List[Dict[str, Any]]] = None,
        index_name: str = "python-logs",
        index_pattern: Optional[str] = None,
        service_name: str = "api",
        project_name: Optional[str] = None,
        environment: str = "development",  # Required: development, staging, production
        console: bool = True,
        **kwargs,
    ):
        super().__init__(name, level)
        if console:
            h = logging.StreamHandler(sys.stdout)
            h.setFormatter(_ConsoleFormatter("%(asctime)s - %(levelname)s - %(name)s - %(message)s"))
            self.addHandler(h)

        from .handlers.otel_handler import OTelHandler

        otel_handler = OTelHandler(
            service_name=service_name,
            environment=environment,
            index_name=index_name,
            level=level,
            **kwargs,
        )
        # Keep structured JSON string output in OTEL body as well.
        otel_handler.setFormatter(JsonFormatter())
        self.addHandler(otel_handler)

    def _log(self, level, msg, args, exc_info=None, extra=None, stack_info=False, stacklevel=1):
        extra = _filter_extra(extra)
        super()._log(level, msg, args, exc_info, extra, stack_info, stacklevel)
