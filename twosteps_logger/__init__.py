"""twosteps_logger package root."""
import logging
import sys
from typing import Dict, Iterable, List, Any, Optional

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


KNOWN_HANDLERS = {"otel", "posthog"}


def _select_handlers(handlers: Optional[Iterable[str]], posthog_api_key: Optional[str]) -> set:
    """Default (None): OTel always, plus PostHog when a key is configured."""
    if handlers is None:
        return {"otel", "posthog"} if posthog_api_key else {"otel"}
    selected = {str(name).strip().lower() for name in handlers if str(name).strip()}
    unknown = selected - KNOWN_HANDLERS
    if unknown:
        print(f"twosteps_logger: ignoring unknown handlers {sorted(unknown)}", file=sys.stderr)
    return selected & KNOWN_HANDLERS


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
        posthog_api_key: Optional[str] = None,
        posthog_host: Optional[str] = None,
        handlers: Optional[Iterable[str]] = None,
        **kwargs,
    ):
        super().__init__(name, level)
        if console:
            h = logging.StreamHandler(sys.stdout)
            h.setFormatter(_ConsoleFormatter("%(asctime)s - %(levelname)s - %(name)s - %(message)s"))
            self.addHandler(h)

        selected = _select_handlers(handlers, posthog_api_key)

        if "otel" in selected:
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

        if "posthog" in selected:
            self._attach_posthog_handler(posthog_api_key, posthog_host, service_name, environment, index_name)

    def _attach_posthog_handler(
        self, api_key: Optional[str], host: Optional[str], service_name: str, environment: str, index_name: str
    ) -> None:
        if not api_key:
            print("twosteps_logger: PostHog handler skipped (no posthog_api_key)", file=sys.stderr)
            return
        try:
            from .handlers.posthog_handler import PostHogHandler

            self.addHandler(
                PostHogHandler(
                    api_key=api_key,
                    host=host,
                    service_name=service_name,
                    environment=environment,
                    index_prefix=index_name,
                )
            )
        except Exception as exc:
            print(f"twosteps_logger: PostHog handler disabled: {exc}", file=sys.stderr)

    def _log(self, level, msg, args, exc_info=None, extra=None, stack_info=False, stacklevel=1):
        extra = _filter_extra(extra)
        super()._log(level, msg, args, exc_info, extra, stack_info, stacklevel)
