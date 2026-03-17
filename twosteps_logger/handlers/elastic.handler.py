import atexit
import logging
import sys
import threading
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set

from ..configuration import ElasticLoggerConfig
from ..formatters import ECSFormatter

# Tracks which index template prefixes have already been created this process lifetime.
# Prevents redundant PUT requests when multiple loggers share the same prefix.
_templates_created: Set[str] = set()


class ElasticsearchHandler(logging.Handler):
    def __init__(self, config: Optional[ElasticLoggerConfig] = None, **kwargs):
        super().__init__()
        if config is None:
            self.config = ElasticLoggerConfig(**kwargs) if kwargs else ElasticLoggerConfig()
        elif isinstance(config, dict):
            self.config = ElasticLoggerConfig(**config)
        else:
            self.config = config
        self._buffer: List[Dict[str, Any]] = []
        self._lock = threading.Lock()
        self._client = None
        self._timer: Optional[threading.Timer] = None
        self._ensure_index_template()
        self._start_flush_timer()
        atexit.register(self._flush_on_exit)

    def _get_client(self):
        if self._client is None:
            try:
                from elasticsearch import Elasticsearch

                self._client = Elasticsearch(**self.config.to_connection_params())
            except ImportError as exc:
                raise ImportError("pip install elasticsearch") from exc
        return self._client

    def _get_index_name(self) -> str:
        pattern = self.config.index_pattern
        now = datetime.now(timezone.utc)
        if "{month}" in pattern:
            return pattern.replace("{month}", now.strftime("%m_%y"))
        if "{date}" in pattern:
            return pattern.replace("{date}", now.strftime("%Y.%m.%d"))
        return pattern

    def _ensure_index_template(self) -> None:
        # Use the full configured prefix (e.g. final-test-logger), not only first token.
        # Otherwise we create broad patterns like final-* that conflict with specific templates.
        prefix = self.config.index_name or "python-logs"
        if prefix in _templates_created:
            return
        try:
            self._get_client().indices.put_index_template(
                name=f"{prefix}-template",
                index_patterns=[f"{prefix}-*"],
                template={
                    "settings": {"number_of_shards": 1},
                    "mappings": {
                        "properties": {
                            "severity": {"type": "keyword"},
                            "message": {"type": "text"},
                            "timestamp": {"type": "date"},
                            "service": {"type": "keyword"},
                            "environment": {"type": "keyword"},
                            "status": {"type": "keyword"},
                        }
                    },
                },
            )
            _templates_created.add(prefix)
        except Exception as exc:  # pragma: no cover
            print(f"[twosteps_logger] template warning: {exc}", file=sys.stderr)

    def _build_document(self, record: logging.LogRecord) -> Dict[str, Any]:
        record.service = self.config.service_name
        record.environment = self.config.environment or "development"
        if isinstance(self.formatter, ECSFormatter):
            return self.formatter._record_to_client_format(record)
        return {
            "severity": record.levelname,
            "message": self.format(record),
            "@timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z",
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z",
            "service": self.config.service_name,
            "environment": self.config.environment or "development",
            "status": getattr(record, "status", "PENDING"),
        }

    def emit(self, record: logging.LogRecord) -> None:
        try:
            doc = self._build_document(record)
            with self._lock:
                self._buffer.append(doc)
                if len(self._buffer) >= self.config.bulk_size:
                    self._flush_buffer()
        except Exception:
            self.handleError(record)

    def _flush_buffer(self) -> None:
        if not self._buffer:
            return
        idx = self._get_index_name()
        bulk_body: List[Dict[str, Any]] = []
        for doc in self._buffer:
            bulk_body.append({"index": {"_index": idx}})
            bulk_body.append(doc)
        self._buffer = []
        try:
            self._get_client().bulk(body=bulk_body, refresh=True)
        except Exception as exc:
            print(f"[twosteps_logger] Error: {exc}", file=sys.stderr)

    def _start_flush_timer(self) -> None:
        def flush():
            with self._lock:
                self._flush_buffer()
            self._timer = threading.Timer(self.config.flush_interval, flush)
            self._timer.daemon = True
            self._timer.start()

        self._timer = threading.Timer(self.config.flush_interval, flush)
        self._timer.daemon = True
        self._timer.start()

    def _flush_on_exit(self) -> None:
        if self._timer:
            self._timer.cancel()
        with self._lock:
            self._flush_buffer()

