from typing import Any

from .logger_configuration import LoggerConfiguration


def get_logger_configuration(**overrides: Any) -> LoggerConfiguration:
    cfg = LoggerConfiguration()
    # Accept story-style and legacy names
    alias_map = {
        "index_prefix": "index_name",
        "service": "service_name",
        "elastic_hosts": "hosts",
    }
    normalized = {}
    for key, value in overrides.items():
        normalized[alias_map.get(key, key)] = value

    if "index_pattern" not in normalized and "index_name" in normalized:
        normalized["index_pattern"] = f"{normalized['index_name']}-{{month}}"

    for key, value in normalized.items():
        if hasattr(cfg, key):
            setattr(cfg, key, value)
    return cfg
