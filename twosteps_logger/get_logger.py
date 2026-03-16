import logging
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from .constants import StatusType
from .configuration import get_logger_configuration

_request_context: ContextVar[Dict[str, Any]] = ContextVar("request_context", default={})
_default_meta: ContextVar[Dict[str, str]] = ContextVar(
    "default_meta", default={"service": "benchmark", "environment": "development"}
)


def set_request_context(**kwargs: Any) -> None:
    current = dict(_request_context.get())
    current.update({k: v for k, v in kwargs.items() if v is not None})
    _request_context.set(current)


def clear_request_context() -> None:
    _request_context.set({})


def get_additional(
    status: StatusType = StatusType.PENDING,
    message: Optional[str] = None,
    auth: Optional[Dict[str, Any]] = None,
    error: Optional[Dict[str, Any]] = None,
    custom_fields: Optional[Dict[str, Any]] = None,
    service: Optional[str] = None,
    environment: Optional[str] = None,
    **kwargs: Any,
) -> Dict[str, Any]:
    defaults = _default_meta.get()
    extras: Dict[str, Any] = {
        "status": status.value if isinstance(status, StatusType) else str(status),
        "message": message,
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z",
        "service": service or defaults.get("service", "benchmark"),
        "environment": environment or defaults.get("environment", "development"),
    }
    extras.update(_request_context.get())
    extras.update({k: v for k, v in kwargs.items() if v is not None})
    if isinstance(auth, dict):
        extras.update(auth)
    if isinstance(error, dict):
        extras.update(error)
    if isinstance(custom_fields, dict):
        extras["custom_fields"] = custom_fields
    return {k: v for k, v in extras.items() if v is not None}


def twosteps_logger(name: str, **kwargs: Any) -> logging.Logger:
    from . import CustomLogger
    resolved_level = kwargs.get("level", kwargs.get("logger_level", logging.INFO))

    config = get_logger_configuration(
        index_prefix=kwargs.get("index_prefix", kwargs.get("index_name", "benchmark")),
        service=kwargs.get("service", kwargs.get("service_name", "benchmark")),
        environment=kwargs.get("environment", "development"),
        elastic_hosts=kwargs.get("elastic_hosts", kwargs.get("hosts")),
        flush_interval=kwargs.get("flush_interval", 1.0),
        bulk_size=kwargs.get("bulk_size", 100),
    )

    # Normalize story-style args before passing to CustomLogger/ElasticLoggerConfig
    kwargs.pop("index_prefix", None)
    kwargs.pop("service", None)
    kwargs.pop("logger_level", None)
    kwargs.pop("hosts", None)

    kwargs.setdefault("index_name", config.index_name)
    kwargs.setdefault("index_pattern", config.index_pattern)
    kwargs.setdefault("service_name", config.service_name)
    kwargs.setdefault("environment", config.environment)
    kwargs.setdefault("level", resolved_level)
    kwargs.setdefault("elastic_hosts", config.hosts)
    kwargs.setdefault("flush_interval", config.flush_interval)
    kwargs.setdefault("bulk_size", config.bulk_size)

    _default_meta.set(
        {
            "service": config.service_name,
            "environment": config.environment or "development",
        }
    )
    return CustomLogger(name=name, **kwargs)
