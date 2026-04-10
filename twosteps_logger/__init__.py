"""twosteps_logger package root."""
import logging
import os
import sys
from typing import Dict, List, Any, Optional

from .handlers import ElasticsearchHandler
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

__version__ = "1.0.0"
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
    Logs go to console + Elasticsearch. View in Kibana.
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
        transport = str(kwargs.pop("logger_transport", kwargs.pop("transport", os.getenv("LOGGER_TRANSPORT", "elastic")))).lower()

        if console:
            h = logging.StreamHandler(sys.stdout)
            h.setFormatter(_ConsoleFormatter("%(asctime)s - %(levelname)s - %(name)s - %(message)s"))
            self.addHandler(h)

        pattern = index_pattern or index_name
        proj = project_name or service_name
        resolved_hosts = elastic_hosts or self._default_hosts_for_env(environment)
        if "username" not in kwargs and "password" not in kwargs:
            env_user, env_pass = self._default_auth_for_env()
            if env_user:
                kwargs["username"] = env_user
            if env_pass:
                kwargs["password"] = env_pass
        if transport in {"otel", "otlp"}:
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
        else:
            es_handler = ElasticsearchHandler(
                hosts=resolved_hosts,
                index_name=index_name,
                index_pattern=pattern,
                service_name=service_name,
                project_name=proj,
                environment=environment,
                **kwargs,
            )
            es_handler.setFormatter(JsonFormatter())
            self.addHandler(es_handler)

    @staticmethod
    def _default_hosts_for_env(environment: str) -> List[Dict[str, Any]]:
        """Resolve fallback ES hosts by environment."""
        env_name = (environment or "development").lower()
        default_host = "localhost" if env_name in {"local", "development"} else "elasticsearch"
        host = os.getenv("ELASTIC_HOST", default_host)
        port = int(os.getenv("ELASTIC_PORT", "9200"))
        scheme = os.getenv("ELASTIC_SCHEME", "http")
        return [{"scheme": scheme, "host": host, "port": port}]
    
    @staticmethod
    def _default_auth_for_env() -> tuple[str | None, str | None]:
        username = os.getenv("ELASTIC_USERNAME")
        password = os.getenv("ELASTIC_PASSWORD")
        return username, password

    def _log(self, level, msg, args, exc_info=None, extra=None, stack_info=False, stacklevel=1):
        extra = _filter_extra(extra)
        super()._log(level, msg, args, exc_info, extra, stack_info, stacklevel)
