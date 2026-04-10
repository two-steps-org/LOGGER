# pyright: reportMissingImports=false
import logging
import os
from typing import Any, Dict, Optional


class OTelHandler(logging.Handler):
    """
    OpenTelemetry logging handler that exports logs to an OTLP collector.
    Defaults:
      - protocol: grpc
      - endpoint: http://localhost:4317 (grpc) / http://localhost:4318 (http)
    """

    def __init__(
        self,
        service_name: str = "api",
        environment: str = "development",
        index_name: str = "python-logs",
        level: int = logging.INFO,
        **kwargs: Any,
    ):
        super().__init__(level)
        self._handler = self._build_handler(
            service_name=service_name,
            environment=environment,
            index_name=index_name,
            **kwargs,
        )

    def _build_handler(
        self,
        service_name: str,
        environment: str,
        index_name: str,
        **kwargs: Any,
    ) -> logging.Handler:
        try:
            from opentelemetry.exporter.otlp.proto.grpc._log_exporter import (
                OTLPLogExporter as GRPCOTLPLogExporter,
            )
            from opentelemetry.exporter.otlp.proto.http._log_exporter import (
                OTLPLogExporter as HTTPOTLPLogExporter,
            )
            from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
            from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
            from opentelemetry.sdk.resources import Resource
        except ImportError as exc:  # pragma: no cover
            raise ImportError(
                "OpenTelemetry dependencies are required for LOGGER_TRANSPORT=otel. "
                "Install: opentelemetry-sdk, "
                "opentelemetry-exporter-otlp-proto-grpc, "
                "opentelemetry-exporter-otlp-proto-http"
            ) from exc

        protocol = str(
            kwargs.get("otlp_protocol")
            or os.getenv("OTEL_EXPORTER_OTLP_PROTOCOL")
            or "grpc"
        ).lower()
        if protocol in {"http", "http/protobuf"}:
            endpoint = kwargs.get("otlp_endpoint") or os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT") or "http://localhost:4318"
            exporter = HTTPOTLPLogExporter(endpoint=endpoint)
        else:
            endpoint = kwargs.get("otlp_endpoint") or os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT") or "http://localhost:4317"
            insecure = str(kwargs.get("otlp_insecure") or os.getenv("OTEL_EXPORTER_OTLP_INSECURE") or "true").lower()
            exporter = GRPCOTLPLogExporter(endpoint=endpoint, insecure=insecure in {"1", "true", "yes"})

        resource = Resource.create(
            {
                "service.name": os.getenv("OTEL_SERVICE_NAME", service_name),
                "deployment.environment": environment,
                "logger.index_prefix": index_name,
            }
        )
        provider = LoggerProvider(resource=resource)
        provider.add_log_record_processor(BatchLogRecordProcessor(exporter))
        handler = LoggingHandler(level=self.level, logger_provider=provider)
        self._provider = provider
        return handler

    def emit(self, record: logging.LogRecord) -> None:
        self._handler.emit(record)

    def close(self) -> None:
        try:
            if hasattr(self, "_provider"):
                self._provider.force_flush()
                self._provider.shutdown()
        except Exception:
            pass
        super().close()
