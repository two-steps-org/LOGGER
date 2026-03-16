import logging
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from .constants import StatusType
from .configuration import get_logger_configuration

_request_context: ContextVar[Dict[str, Any]] = ContextVar("request_context", default={})
_default_meta: ContextVar[Dict[str, str]] = ContextVar(
    "default_meta", default={"service": "api", "environment": "development"}
)
_logger_defaults: ContextVar[Dict[str, Any]] = ContextVar("logger_defaults", default={})


def set_request_context(**kwargs: Any) -> None:
    current = dict(_request_context.get())
    current.update({k: v for k, v in kwargs.items() if v is not None})
    _request_context.set(current)


def clear_request_context() -> None:
    _request_context.set({})


def setup_logger(
    *,
    index_prefix: Optional[str] = None,
    index_name: Optional[str] = None,
    service: Optional[str] = None,
    service_name: Optional[str] = None,
    environment: Optional[str] = None,
    level: Optional[int] = None,
    logger_level: Optional[int] = None,
    elastic_hosts: Optional[Any] = None,
    hosts: Optional[Any] = None,
    flush_interval: Optional[float] = None,
    bulk_size: Optional[int] = None,
) -> None:
    """Set process-level defaults so callers can use get_logger(name) only."""
    defaults = dict(_logger_defaults.get())
    resolved_index = index_prefix or index_name
    resolved_service = service or service_name
    resolved_level = level if level is not None else logger_level
    resolved_hosts = elastic_hosts if elastic_hosts is not None else hosts

    if resolved_index is not None:
        defaults["index_prefix"] = resolved_index
    if resolved_service is not None:
        defaults["service"] = resolved_service
    if environment is not None:
        defaults["environment"] = environment
    if resolved_level is not None:
        defaults["level"] = resolved_level
    if resolved_hosts is not None:
        defaults["elastic_hosts"] = resolved_hosts
    if flush_interval is not None:
        defaults["flush_interval"] = flush_interval
    if bulk_size is not None:
        defaults["bulk_size"] = bulk_size

    _logger_defaults.set(defaults)


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
        "service": service or defaults.get("service", "api"),
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
    defaults = _logger_defaults.get()
    resolved_level = kwargs.get(
        "level",
        kwargs.get("logger_level", defaults.get("level", logging.INFO)),
    )
    resolved_index_prefix = kwargs.get(
        "index_prefix",
        kwargs.get("index_name", defaults.get("index_prefix", "python-logs")),
    )
    resolved_service = kwargs.get(
        "service",
        kwargs.get("service_name", defaults.get("service", "api")),
    )
    resolved_environment = kwargs.get("environment", defaults.get("environment", "development"))
    resolved_hosts = kwargs.get(
        "elastic_hosts",
        kwargs.get("hosts", defaults.get("elastic_hosts")),
    )
    resolved_flush_interval = kwargs.get("flush_interval", defaults.get("flush_interval", 1.0))
    resolved_bulk_size = kwargs.get("bulk_size", defaults.get("bulk_size", 100))

    config = get_logger_configuration(
        index_prefix=resolved_index_prefix,
        service=resolved_service,
        environment=resolved_environment,
        elastic_hosts=resolved_hosts,
        flush_interval=resolved_flush_interval,
        bulk_size=resolved_bulk_size,
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


def get_logger(name: str, **kwargs: Any) -> logging.Logger:
    """Convenience alias for twosteps_logger(name, **kwargs)."""
    return twosteps_logger(name=name, **kwargs)
