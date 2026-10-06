import logging
import os
from typing import Optional

DEFAULT_HOST = "https://us.i.posthog.com"
_LOGS_PATH = "/i/v1/logs"


class PostHogHandler(logging.Handler):
    """Ships INFO+ records to PostHog over OTLP/HTTP using a background batch processor."""

    def __init__(
        self,
        api_key: str,
        host: Optional[str] = None,
        service_name: str = "api",
        environment: str = "development",
        level: int = logging.INFO,
        timeout: float = 5.0,
        index_prefix: Optional[str] = None,
    ):
        super().__init__(max(level, logging.INFO))
        self._provider = None
        self._handler = None
        if os.getenv("OTEL_SDK_DISABLED", "").lower() == "true":
            return
        self._provider = self._build_provider(api_key, host, service_name, environment, timeout, index_prefix)
        from opentelemetry.sdk._logs import LoggingHandler

        self._handler = LoggingHandler(level=logging.NOTSET, logger_provider=self._provider)

    @staticmethod
    def _logs_endpoint(host: Optional[str]) -> str:
        base = (host or DEFAULT_HOST).rstrip("/")
        return base if base.endswith(_LOGS_PATH) else base + _LOGS_PATH

    @staticmethod
    def _build_provider(api_key, host, service_name, environment, timeout, index_prefix=None):
        from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter
        from opentelemetry.sdk._logs import LoggerProvider
        from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
        from opentelemetry.sdk.resources import Resource

        exporter = OTLPLogExporter(
            endpoint=PostHogHandler._logs_endpoint(host),
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=timeout,
        )
        attributes = {"service.name": service_name, "deployment.environment": environment}
        if index_prefix:
            attributes["logger.index_prefix"] = index_prefix
        provider = LoggerProvider(resource=Resource.create(attributes))
        provider.add_log_record_processor(
            BatchLogRecordProcessor(exporter, export_timeout_millis=timeout * 1000)
        )
        return provider

    def emit(self, record: logging.LogRecord) -> None:
        if self._handler is None:
            return
        try:
            self._handler.emit(record)
        except Exception:
            self.handleError(record)

    def close(self) -> None:
        if self._provider is not None:
            try:
                self._provider.force_flush()
                self._provider.shutdown()
            except Exception:
                pass
        super().close()
